import hashlib
import os
import shutil
import subprocess
import re
import time
from collections.abc import Mapping
import torch

import server
from .logger import logger

BIGMIN = -(2**53-1)
BIGMAX = (2**53-1)

DIMMAX = 8192

ENCODE_ARGS = ("utf-8", 'backslashreplace')

def ffmpeg_suitability(path):
    try:
        version = subprocess.run([path, "-version"], check=True,
                                 capture_output=True).stdout.decode(*ENCODE_ARGS)
    except:
        return 0
    score = 0
    #rough layout of the importance of various features
    simple_criterion = [("libvpx", 20),("264",10), ("265",3),
                        ("svtav1",5),("libopus", 1)]
    for criterion in simple_criterion:
        if version.find(criterion[0]) >= 0:
            score += criterion[1]
    #obtain rough compile year from copyright information
    copyright_index = version.find('2000-2')
    if copyright_index >= 0:
        copyright_year = version[copyright_index+6:copyright_index+9]
        if copyright_year.isnumeric():
            score += int(copyright_year)
    return score

class MultiInput(str):
    def __new__(cls, string, allowed_types="*"):
        res = super().__new__(cls, string)
        res.allowed_types=allowed_types
        return res
    def __ne__(self, other):
        if self.allowed_types == "*" or other == "*":
            return False
        return other not in self.allowed_types
imageOrLatent = MultiInput("IMAGE", ["IMAGE", "LATENT"])
floatOrInt = MultiInput("FLOAT", ["FLOAT", "INT"])

class ContainsAll(dict):
    def __contains__(self, other):
        return True
    def __getitem__(self, key):
        return super().get(key, (None, {}))

if "VHS_FORCE_FFMPEG_PATH" in os.environ:
    ffmpeg_path = os.environ.get("VHS_FORCE_FFMPEG_PATH")
else:
    ffmpeg_paths = []
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        imageio_ffmpeg_path = get_ffmpeg_exe()
        ffmpeg_paths.append(imageio_ffmpeg_path)
    except:
        if "VHS_USE_IMAGEIO_FFMPEG" in os.environ:
            raise
        logger.warn("Failed to import imageio_ffmpeg")
    if "VHS_USE_IMAGEIO_FFMPEG" in os.environ:
        ffmpeg_path = imageio_ffmpeg_path
    else:
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg is not None:
            ffmpeg_paths.append(system_ffmpeg)
        if os.path.isfile("ffmpeg"):
            ffmpeg_paths.append(os.path.abspath("ffmpeg"))
        if os.path.isfile("ffmpeg.exe"):
            ffmpeg_paths.append(os.path.abspath("ffmpeg.exe"))
        if len(ffmpeg_paths) == 0:
            logger.error("No valid ffmpeg found.")
            ffmpeg_path = None
        elif len(ffmpeg_paths) == 1:
            #Evaluation of suitability isn't required, can take sole option
            #to reduce startup time
            ffmpeg_path = ffmpeg_paths[0]
        else:
            ffmpeg_path = max(ffmpeg_paths, key=ffmpeg_suitability)
gifski_path = os.environ.get("VHS_GIFSKI", None)
if gifski_path is None:
    gifski_path = os.environ.get("JOV_GIFSKI", None)
    if gifski_path is None:
        gifski_path = shutil.which("gifski")


# modified from https://stackoverflow.com/questions/22058048/hashing-a-file-in-python
def calculate_file_hash(filename: str, hash_every_n: int = 1):
    #Larger video files were taking >.5 seconds to hash even when cached,
    #so instead the modified time from the filesystem is used as a hash
    h = hashlib.sha256()
    h.update(filename.encode())
    h.update(str(os.path.getmtime(filename)).encode())
    return h.hexdigest()

prompt_queue = server.PromptServer.instance.prompt_queue
def requeue_workflow_unchecked():
    """Requeues the current workflow without checking for multiple requeues"""
    currently_running = prompt_queue.currently_running
    value = next(iter(currently_running.values()))

    # Handle both old (5 values) and new (6 values) ComfyUI versions
    if len(value) == 6:
        (_, prompt_id, prompt, extra_data, outputs_to_execute, _) = value
    else:
        (_, prompt_id, prompt, extra_data, outputs_to_execute) = value

    #Ensure batch_managers are marked stale
    prompt = prompt.copy()
    for uid in prompt:
        if prompt[uid]['class_type'] == 'VHS_BatchManager':
            inputs = prompt[uid]['inputs']
            prompt[uid] = {**prompt[uid], 'inputs': {**inputs, 'requeue': inputs.get('requeue', 0) + 1}}

    #execution.py has guards for concurrency, but server doesn't.
    #TODO: Check that this won't be an issue
    number = -server.PromptServer.instance.number
    server.PromptServer.instance.number += 1
    prompt_id = str(server.uuid.uuid4())
    prompt_queue.put((number, prompt_id, prompt, extra_data, outputs_to_execute, *value[5:]))

requeue_guard = [None, 0, 0, {}]

def requeue_workflow(requeue_required=(-1,True)):
    assert(len(prompt_queue.currently_running) == 1)
    global requeue_guard

    value = next(iter(prompt_queue.currently_running.values()))

    # Handle both old (5 values) and new (6 values) ComfyUI versions
    if len(value) == 6:
        (run_number, _, prompt, extra_data, outputs_to_execute, _) = value
    else:
        (run_number, _, prompt, extra_data, outputs_to_execute) = value

    if requeue_guard[0] != run_number:
        #Calculate a count of how many outputs are managed by a batch manager
        managed_outputs=0
        for bm_uid in prompt:
            if prompt[bm_uid]['class_type'] == 'VHS_BatchManager':
                for output_uid in prompt:
                    if prompt[output_uid]['class_type'] in ["VHS_VideoCombine"]:
                        for inp in prompt[output_uid]['inputs'].values():
                            if inp == [bm_uid, 0]:
                                managed_outputs+=1
        requeue_guard = [run_number, 0, managed_outputs, {}]
    requeue_guard[1] = requeue_guard[1]+1
    requeue_guard[3][requeue_required[0]] = requeue_required[1]
    if requeue_guard[1] == requeue_guard[2] and max(requeue_guard[3].values()):
        requeue_workflow_unchecked()

# Constrain the demuxer when reading uploaded videos with these extensions.
_LOCAL_VIDEO_FORMATS = {
    ".mp4": "mov", ".mov": "mov", ".m4v": "mov", ".webm": "matroska",
    ".mkv": "matroska", ".gif": "gif", ".webp": "webp_pipe", ".avi": "avi",
}


def local_video_input(path):
    demuxer = _LOCAL_VIDEO_FORMATS.get(os.path.splitext(path)[1].lower())
    if demuxer:
        return ["-protocol_whitelist", "file,pipe", "-f", demuxer, "-i", path]
    return ["-i", path]


def get_audio(file, start_time=0, duration=0):
    args = [ffmpeg_path, *local_video_input(file)]
    if start_time > 0:
        args += ["-ss", str(start_time)]
    if duration > 0:
        args += ["-t", str(duration)]
    try:
        #TODO: scan for sample rate and maintain
        res =  subprocess.run(args + ["-f", "f32le", "-"],
                              capture_output=True, check=True)
        audio = torch.frombuffer(bytearray(res.stdout), dtype=torch.float32)
        match = re.search(', (\\d+) Hz, (\\w+), ',res.stderr.decode(*ENCODE_ARGS))
    except subprocess.CalledProcessError as e:
        raise Exception(f"VHS failed to extract audio from {file}:\n" \
                + e.stderr.decode(*ENCODE_ARGS))
    if match:
        ar = int(match.group(1))
        #NOTE: Just throwing an error for other channel types right now
        #Will deal with issues if they come
        ac = {"mono": 1, "stereo": 2}[match.group(2)]
    else:
        ar = 44100
        ac = 2
    audio = audio.reshape((-1,ac)).transpose(0,1).unsqueeze(0)
    return {'waveform': audio, 'sample_rate': ar}

class LazyAudioMap(Mapping):
    def __init__(self, file, start_time, duration):
        self.file = file
        self.start_time=start_time
        self.duration=duration
        self._dict=None
    def __getitem__(self, key):
        if self._dict is None:
            self._dict = get_audio(self.file, self.start_time, self.duration)
        return self._dict[key]
    def __iter__(self):
        if self._dict is None:
            self._dict = get_audio(self.file, self.start_time, self.duration)
        return iter(self._dict)
    def __len__(self):
        if self._dict is None:
            self._dict = get_audio(self.file, self.start_time, self.duration)
        return len(self._dict)
def lazy_get_audio(file, start_time=0, duration=0, **kwargs):
    return LazyAudioMap(file, start_time, duration)


def strip_path(path):
    #This leaves whitespace inside quotes and only a single "
    #thus ' ""test"' -> '"test'
    #consider path.strip(string.whitespace+"\"")
    #or weightier re.fullmatch("[\\s\"]*(.+?)[\\s\"]*", path).group(1)
    path = path.strip()
    if path.startswith("\""):
        path = path[1:]
    if path.endswith("\""):
        path = path[:-1]
    return path


def merge_filter_args(args, ftype="-vf"):
    #TODO This doesn't account for filter_complex
    #Will likely need to convert all filters to filter complex in the future
    #But that requires source/output deduplication
    try:
        start_index = args.index(ftype)+1
        index = start_index
        while True:
            index = args.index(ftype, index)
            args[start_index] += ',' + args[index+1]
            args.pop(index)
            args.pop(index)
    except ValueError:
        pass


def cached(duration):
    def dec(f):
        cached_ret = None
        cache_time = 0
        def cached_func():
            nonlocal cache_time, cached_ret
            if time.time() > cache_time + duration or cached_ret is None:
                cache_time = time.time()
                cached_ret = f()
            return cached_ret
        return cached_func
    return dec
