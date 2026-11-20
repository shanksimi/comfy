"""VideoHelperSuite nodes used by the video upscale workflow (GPL-3.0)."""

import folder_paths

from ..load_image_metadata import _action_media_path
from .videohelpersuite import nodes as vhs
from .videohelpersuite.load_video_nodes import LoadVideoFFmpegUpload
from .videohelpersuite.utils import calculate_file_hash


class LoadVideoFFmpeg(LoadVideoFFmpegUpload):
    @classmethod
    def INPUT_TYPES(cls):
        inputs = super().INPUT_TYPES()
        inputs["required"]["start_time"][1].pop("widgetType", None)
        inputs["optional"]["format"][1]["default"] = "None"
        return inputs

    @staticmethod
    def _input_path(video):
        if not isinstance(video, str) or not video:
            raise ValueError("Select an input video")
        return _action_media_path(folder_paths.get_input_directory(), video.removesuffix(" [input]"), "video")

    def load_video(self, video, **kwargs):
        return super().load_video(video=self._input_path(video), **kwargs)

    @classmethod
    def IS_CHANGED(cls, video, **kwargs):
        try:
            return calculate_file_hash(cls._input_path(video))
        except (OSError, ValueError):
            return float("nan")

    @classmethod
    def VALIDATE_INPUTS(cls, video):
        try:
            cls._input_path(video)
        except (OSError, ValueError) as error:
            return str(error)
        return True


NODE_CLASS_MAPPINGS = {
    "VHS_LoadVideoFFmpeg": LoadVideoFFmpeg,
    "VHS_VideoCombine": vhs.VideoCombine,
    "VHS_BatchManager": vhs.BatchManager,
    "VHS_VideoInfoLoaded": vhs.VideoInfoLoaded,
}
NODE_DISPLAY_NAME_MAPPINGS = {node: vhs.NODE_DISPLAY_NAME_MAPPINGS[node] for node in NODE_CLASS_MAPPINGS}
