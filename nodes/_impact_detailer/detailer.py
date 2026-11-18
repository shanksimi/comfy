# Adapted from ComfyUI-Impact-Pack at 61b9388. See LICENSE.txt.
import logging

import comfy.samplers
import torch
import nodes
from nodes import MAX_RESOLUTION

from . import core, hooks, utils, wildcards
from .core import SEG


def _detailer_cycle_images(image, detailer_hook, cycle):
    if hooks.get_detailer_options(detailer_hook).get("return_by_cycle_step", False):
        image = image.cpu()
        return [image.clone() for _ in range(cycle)]
    return None


def _paste_detail_images(image, enhanced_image, mask, crop_region, detailer_hook, images_by_cycle, cycle_images):
    targets = [image] if images_by_cycle is None else images_by_cycle
    patches = cycle_images if cycle_images else [enhanced_image] * len(targets)
    for i, (target, patch) in enumerate(zip(targets, patches)):
        utils.tensor_paste(target, patch, (crop_region[0], crop_region[1]), mask)
        if detailer_hook is not None:
            if images_by_cycle is not None:
                detailer_hook.set_steps((i, len(targets)))
            target = detailer_hook.post_paste(target)
        targets[i] = target
    return targets[-1]



def _sorted_by_crop_size(outputs):
    # Sampled-size crops keep the order of their crops, so the per-region output lists stay paired.
    return [image for _, image in sorted(outputs, key=lambda output: output[0], reverse=True)]


class DetailerForEach:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                    "image": ("IMAGE", ),
                    "segs": ("SEGS", ),
                    "model": ("MODEL", {"tooltip": "If the `ImpactDummyInput` is connected to the model, the inference stage is skipped."}),
                    "clip": ("CLIP",),
                    "vae": ("VAE",),
                    "guide_size": ("FLOAT", {"default": 512, "min": 64, "max": nodes.MAX_RESOLUTION, "step": 8}),
                    "guide_size_for": ("BOOLEAN", {"default": True, "label_on": "bbox", "label_off": "crop_region"}),
                    "max_size": ("FLOAT", {"default": 1024, "min": 64, "max": nodes.MAX_RESOLUTION, "step": 8}),
                    "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                    "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                    "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0}),
                    "sampler_name": (comfy.samplers.KSampler.SAMPLERS,),
                    "scheduler": (core.get_schedulers(),),
                    "positive": ("CONDITIONING",),
                    "negative": ("CONDITIONING",),
                    "denoise": ("FLOAT", {"default": 0.5, "min": 0.0001, "max": 1.0, "step": 0.01}),
                    "feather": ("INT", {"default": 5, "min": 0, "max": 100, "step": 1}),
                    "noise_mask": ("BOOLEAN", {"default": True, "label_on": "enabled", "label_off": "disabled"}),
                    "force_inpaint": ("BOOLEAN", {"default": True, "label_on": "enabled", "label_off": "disabled"}),
                    "wildcard": ("STRING", {"multiline": True, "dynamicPrompts": False}),

                    "cycle": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
                   },
                "optional": {
                    "detailer_hook": ("DETAILER_HOOK",),
                    "inpaint_model": ("BOOLEAN", {"default": False, "label_on": "enabled", "label_off": "disabled"}),
                    "noise_mask_feather": ("INT", {"default": 20, "min": 0, "max": 100, "step": 1}),
                    "scheduler_func_opt": ("SCHEDULER_FUNC",),
                    "tiled_encode": ("BOOLEAN", {"default": False, "label_on": "enabled", "label_off": "disabled"}),
                    "tiled_decode": ("BOOLEAN", {"default": False, "label_on": "enabled", "label_off": "disabled"}),
                   }
                }

    RETURN_TYPES = ("IMAGE", )
    FUNCTION = "doit"

    CATEGORY = "ImpactPack/Detailer"

    DESCRIPTION = "It enhances details by inpainting each region within the detected area bundle (SEGS) after enlarging them based on the guide size."

    @staticmethod
    def get_core_module():
        return core

    @staticmethod
    def do_detail(image, segs, model, clip, vae, guide_size, guide_size_for_bbox, max_size, seed, steps, cfg, sampler_name, scheduler,
                  positive, negative, denoise, feather, noise_mask, force_inpaint, wildcard_opt=None, detailer_hook=None,
                  refiner_ratio=None, refiner_model=None, refiner_clip=None, refiner_positive=None, refiner_negative=None,
                  cycle=1, inpaint_model=False, noise_mask_feather=0, scheduler_func_opt=None, tiled_encode=False, tiled_decode=False):

        if len(image) > 1:
            raise Exception('[Impact Pack] ERROR: DetailerForEach does not allow image batches.\nPlease refer to https://github.com/ltdrdata/ComfyUI-extension-tutorials/blob/Main/ComfyUI-Impact-Pack/tutorial/batching-detailer.md for more information.')

        image = image.clone()
        images_by_cycle = _detailer_cycle_images(image, detailer_hook, cycle)
        upscaled_crops = hooks.get_detailer_options(detailer_hook).get("return_upscaled_crops", False)
        enhanced_alpha_list = []
        enhanced_list = []
        cropped_list = []
        cnet_pil_list = []

        segs = core.segs_scale_match(segs, image.shape)
        new_segs = []

        wildcard_concat_mode = None
        if wildcard_opt is not None:
            if wildcard_opt.startswith('[CONCAT]'):
                wildcard_concat_mode = 'concat'
                wildcard_opt = wildcard_opt[8:]
            wmode, wildcard_chooser = wildcards.process_wildcard_for_segs(wildcard_opt)
        else:
            wmode, wildcard_chooser = None, None

        if wmode in ['ASC', 'DSC', 'ASC-SIZE', 'DSC-SIZE']:
            if wmode == 'ASC':
                ordered_segs = sorted(segs[1], key=lambda x: (x.bbox[0], x.bbox[1]))
            elif wmode == 'DSC':
                ordered_segs = sorted(segs[1], key=lambda x: (x.bbox[0], x.bbox[1]), reverse=True)
            elif wmode == 'ASC-SIZE':
                ordered_segs = sorted(segs[1], key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]))

            else:   # wmode == 'DSC-SIZE'
                ordered_segs = sorted(segs[1], key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]), reverse=True)
        else:
            ordered_segs = segs[1]

        if not (isinstance(model, str) and model == "DUMMY") and noise_mask_feather > 0 and 'denoise_mask_function' not in model.model_options:
            model = utils.apply_differential_diffusion(model)

        for i, seg in enumerate(ordered_segs):
            cropped_image = utils.crop_ndarray4(image.cpu().numpy(), seg.crop_region)  # Never use seg.cropped_image to handle overlapping area
            cropped_image = utils.to_tensor(cropped_image)
            mask = utils.to_tensor(seg.cropped_mask)
            mask = utils.tensor_gaussian_blur_mask(mask, feather)

            is_mask_all_zeros = (seg.cropped_mask == 0).all().item()
            if is_mask_all_zeros:
                logging.info("Detailer: segment skip [empty mask]")
                continue

            if noise_mask:
                cropped_mask = seg.cropped_mask
            else:
                cropped_mask = None

            if wildcard_chooser is not None and wmode != "LAB":
                seg_seed, wildcard_item = wildcard_chooser.get(seg)
            elif wildcard_chooser is not None and wmode == "LAB":
                seg_seed, wildcard_item = None, wildcard_chooser.get(seg)
            else:
                seg_seed, wildcard_item = None, None

            seg_seed = seed + i if seg_seed is None else seg_seed

            if not isinstance(positive, str):
                cropped_positive = [
                    [condition, {
                        k: core.crop_condition_mask(v, image, seg.crop_region) if k == "mask" else v
                        for k, v in details.items()
                    }]
                    for condition, details in positive
                ]
            else:
                cropped_positive = positive

            if not isinstance(negative, str):
                cropped_negative = [
                    [condition, {
                        k: core.crop_condition_mask(v, image, seg.crop_region) if k == "mask" else v
                        for k, v in details.items()
                    }]
                    for condition, details in negative
                ]
            else:
                # Negative Conditioning is placeholder such as FLUX.1
                cropped_negative = negative

            if wildcard_item and wildcard_item.strip() == '[SKIP]':
                continue

            if wildcard_item and wildcard_item.strip() == '[STOP]':
                break

            orig_cropped_image = cropped_image.clone()
            cycle_images = [] if images_by_cycle is not None else None
            upscaled_images = [] if upscaled_crops else None
            if not (isinstance(model, str) and model == "DUMMY"):
                enhanced_image, cnet_pils = core.enhance_detail(cropped_image, model, clip, vae, guide_size, guide_size_for_bbox, max_size,
                                                                seg.bbox, seg_seed, steps, cfg, sampler_name, scheduler,
                                                                cropped_positive, cropped_negative, denoise, cropped_mask, force_inpaint,
                                                                wildcard_opt=wildcard_item, wildcard_opt_concat_mode=wildcard_concat_mode,
                                                                detailer_hook=detailer_hook,
                                                                refiner_ratio=refiner_ratio, refiner_model=refiner_model,
                                                                refiner_clip=refiner_clip, refiner_positive=refiner_positive,
                                                                refiner_negative=refiner_negative, control_net_wrapper=seg.control_net_wrapper,
                                                                cycle=cycle, inpaint_model=inpaint_model, noise_mask_feather=noise_mask_feather,
                                                                scheduler_func=scheduler_func_opt, vae_tiled_encode=tiled_encode,
                                                                vae_tiled_decode=tiled_decode, cycle_images=cycle_images,
                                                                upscaled_images=upscaled_images)
            else:
                enhanced_image = cropped_image
                cnet_pils = None

            if cnet_pils is not None:
                cnet_pil_list.extend(cnet_pils)

            if enhanced_image is not None:
                # don't latent composite-> converting to latent caused poor quality
                # use image paste
                image = image.cpu()
                enhanced_image = enhanced_image.cpu()
                image = _paste_detail_images(image, enhanced_image, mask, seg.crop_region, detailer_hook, images_by_cycle, cycle_images)
                enhanced_list.append((enhanced_image.shape, upscaled_images[1] if upscaled_images else enhanced_image))

            if enhanced_image is not None:
                # Convert enhanced_pil_alpha to RGBA mode
                enhanced_image_alpha = utils.tensor_convert_rgba(enhanced_image)
                new_seg_image = enhanced_image.numpy()  # alpha should not be applied to seg_image

                # Apply the mask
                mask = utils.tensor_resize(mask, *utils.tensor_get_size(enhanced_image))
                utils.tensor_putalpha(enhanced_image_alpha, mask)
                enhanced_alpha_list.append(enhanced_image_alpha)
            else:
                new_seg_image = None

            cropped_list.append((orig_cropped_image.shape, upscaled_images[0] if upscaled_images else orig_cropped_image)) # NOTE: Don't use `cropped_image`

            new_seg = SEG(new_seg_image, seg.cropped_mask, seg.confidence, seg.crop_region, seg.bbox, seg.label, seg.control_net_wrapper)
            new_segs.append(new_seg)

        image_tensor = utils.tensor_convert_rgb(image if images_by_cycle is None else torch.cat(images_by_cycle))

        cropped_list = _sorted_by_crop_size(cropped_list)
        enhanced_list = _sorted_by_crop_size(enhanced_list)
        enhanced_alpha_list.sort(key=lambda x: x.shape, reverse=True)

        return image_tensor, cropped_list, enhanced_list, enhanced_alpha_list, cnet_pil_list, (segs[0], new_segs)

    def doit(self, image, segs, model, clip, vae, guide_size, guide_size_for, max_size, seed, steps, cfg, sampler_name,
             scheduler, positive, negative, denoise, feather, noise_mask, force_inpaint, wildcard, cycle=1,
             detailer_hook=None, inpaint_model=False, noise_mask_feather=0, scheduler_func_opt=None,
             tiled_encode=False, tiled_decode=False):

        enhanced_img, *_ = \
            DetailerForEach.do_detail(image, segs, model, clip, vae, guide_size, guide_size_for, max_size, seed, steps,
                                      cfg, sampler_name, scheduler, positive, negative, denoise, feather, noise_mask,
                                      force_inpaint, wildcard, detailer_hook,
                                      cycle=cycle, inpaint_model=inpaint_model, noise_mask_feather=noise_mask_feather,
                                      scheduler_func_opt=scheduler_func_opt, tiled_encode=tiled_encode, tiled_decode=tiled_decode)

        return (enhanced_img, )


class FaceDetailer:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {
                     "image": ("IMAGE", ),
                     "model": ("MODEL", {"tooltip": "If the `ImpactDummyInput` is connected to the model, the inference stage is skipped."}),
                     "clip": ("CLIP",),
                     "vae": ("VAE",),
                     "guide_size": ("FLOAT", {"default": 512, "min": 64, "max": nodes.MAX_RESOLUTION, "step": 8}),
                     "guide_size_for": ("BOOLEAN", {"default": True, "label_on": "bbox", "label_off": "crop_region"}),
                     "max_size": ("FLOAT", {"default": 1024, "min": 64, "max": nodes.MAX_RESOLUTION, "step": 8}),
                     "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                     "steps": ("INT", {"default": 20, "min": 1, "max": 10000}),
                     "cfg": ("FLOAT", {"default": 8.0, "min": 0.0, "max": 100.0}),
                     "sampler_name": (comfy.samplers.KSampler.SAMPLERS,),
                     "scheduler": (core.get_schedulers(),),
                     "positive": ("CONDITIONING",),
                     "negative": ("CONDITIONING",),
                     "denoise": ("FLOAT", {"default": 0.5, "min": 0.0001, "max": 1.0, "step": 0.01}),
                     "feather": ("INT", {"default": 5, "min": 0, "max": 100, "step": 1}),
                     "noise_mask": ("BOOLEAN", {"default": True, "label_on": "enabled", "label_off": "disabled"}),
                     "force_inpaint": ("BOOLEAN", {"default": True, "label_on": "enabled", "label_off": "disabled"}),

                     "bbox_threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                     "bbox_dilation": ("INT", {"default": 10, "min": -512, "max": 512, "step": 1}),
                     "bbox_crop_factor": ("FLOAT", {"default": 3.0, "min": 1.0, "max": 10, "step": 0.1}),

                     "sam_detection_hint": (["center-1", "horizontal-2", "vertical-2", "rect-4", "diamond-4", "mask-area", "mask-points", "mask-point-bbox", "none"],),
                     "sam_dilation": ("INT", {"default": 0, "min": -512, "max": 512, "step": 1}),
                     "sam_threshold": ("FLOAT", {"default": 0.93, "min": 0.0, "max": 1.0, "step": 0.01}),
                     "sam_bbox_expansion": ("INT", {"default": 0, "min": 0, "max": 1000, "step": 1}),
                     "sam_mask_hint_threshold": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.01}),
                     "sam_mask_hint_use_negative": (["False", "Small", "Outter"],),

                     "drop_size": ("INT", {"min": 1, "max": MAX_RESOLUTION, "step": 1, "default": 10}),

                     "bbox_detector": ("BBOX_DETECTOR", ),
                     "wildcard": ("STRING", {"multiline": True, "dynamicPrompts": False}),

                     "cycle": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1}),
                     },
                "optional": {
                    "sam_model_opt": ("SAM_MODEL", ),
                    "segm_detector_opt": ("SEGM_DETECTOR", ),
                    "detailer_hook": ("DETAILER_HOOK",),
                    "inpaint_model": ("BOOLEAN", {"default": False, "label_on": "enabled", "label_off": "disabled"}),
                    "noise_mask_feather": ("INT", {"default": 20, "min": 0, "max": 100, "step": 1}),
                    "scheduler_func_opt": ("SCHEDULER_FUNC",),
                    "tiled_encode": ("BOOLEAN", {"default": False, "label_on": "enabled", "label_off": "disabled"}),
                    "tiled_decode": ("BOOLEAN", {"default": False, "label_on": "enabled", "label_off": "disabled"}),
                }}

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "MASK", "DETAILER_PIPE", "IMAGE")
    RETURN_NAMES = ("image", "cropped_refined", "cropped_enhanced_alpha", "mask", "detailer_pipe", "cnet_images")
    OUTPUT_IS_LIST = (False, True, True, False, False, True)
    FUNCTION = "doit"

    CATEGORY = "ImpactPack/Simple"

    DESCRIPTION = "This node enhances details by automatically detecting specific objects in the input image using detection models (bbox, segm, sam) and regenerating the image by enlarging the detected area based on the guide size.\nAlthough this node is specialized to simplify the commonly used facial detail enhancement workflow, it can also be used for various automatic inpainting purposes depending on the detection model."

    @staticmethod
    def enhance_face(image, model, clip, vae, guide_size, guide_size_for_bbox, max_size, seed, steps, cfg, sampler_name, scheduler,
                     positive, negative, denoise, feather, noise_mask, force_inpaint,
                     bbox_threshold, bbox_dilation, bbox_crop_factor,
                     sam_detection_hint, sam_dilation, sam_threshold, sam_bbox_expansion, sam_mask_hint_threshold,
                     sam_mask_hint_use_negative, drop_size,
                     bbox_detector, segm_detector=None, sam_model_opt=None, wildcard_opt=None, detailer_hook=None,
                     refiner_ratio=None, refiner_model=None, refiner_clip=None, refiner_positive=None, refiner_negative=None, cycle=1,
                     inpaint_model=False, noise_mask_feather=0, scheduler_func_opt=None, tiled_encode=False, tiled_decode=False):

        # make default prompt as 'face' if empty prompt for CLIPSeg
        bbox_detector.setAux('face')
        try:
            segs = bbox_detector.detect(image, bbox_threshold, bbox_dilation, bbox_crop_factor, drop_size, detailer_hook=detailer_hook)
        finally:
            bbox_detector.setAux(None)

        # bbox + sam combination
        if sam_model_opt is not None:
            sam_mask = core.make_sam_mask(sam_model_opt, segs, image, sam_detection_hint, sam_dilation,
                                          sam_threshold, sam_bbox_expansion, sam_mask_hint_threshold,
                                          sam_mask_hint_use_negative, )
            segs = core.segs_bitwise_and_mask(segs, sam_mask)

        elif segm_detector is not None:
            segm_segs = segm_detector.detect(image, bbox_threshold, bbox_dilation, bbox_crop_factor, drop_size)
            detection_hook = hooks.get_detailer_detection_hook(detailer_hook)

            if (hasattr(segm_detector, 'override_bbox_by_segm') and segm_detector.override_bbox_by_segm and
                    not (detection_hook is not None and not hasattr(detection_hook, 'override_bbox_by_segm'))):
                segs = segm_segs
            else:
                segm_mask = core.segs_to_combined_mask(segm_segs)
                segs = core.segs_bitwise_and_mask(segs, segm_mask)

        if len(segs[1]) > 0:
            enhanced_img, _, cropped_enhanced, cropped_enhanced_alpha, cnet_pil_list, new_segs = \
                DetailerForEach.do_detail(image, segs, model, clip, vae, guide_size, guide_size_for_bbox, max_size, seed, steps, cfg,
                                          sampler_name, scheduler, positive, negative, denoise, feather, noise_mask,
                                          force_inpaint, wildcard_opt, detailer_hook,
                                          refiner_ratio=refiner_ratio, refiner_model=refiner_model,
                                          refiner_clip=refiner_clip, refiner_positive=refiner_positive,
                                          refiner_negative=refiner_negative,
                                          cycle=cycle, inpaint_model=inpaint_model, noise_mask_feather=noise_mask_feather,
                                          scheduler_func_opt=scheduler_func_opt, tiled_encode=tiled_encode, tiled_decode=tiled_decode)
        else:
            images_by_cycle = _detailer_cycle_images(image, detailer_hook, cycle)
            enhanced_img = image if images_by_cycle is None else torch.cat(images_by_cycle)
            cropped_enhanced = []
            cropped_enhanced_alpha = []
            cnet_pil_list = []

        # Mask Generator
        mask = core.segs_to_combined_mask(segs)
        if hooks.get_detailer_options(detailer_hook).get("return_by_cycle_step", False):
            mask = mask.unsqueeze(0).repeat(len(enhanced_img), 1, 1)

        if len(cropped_enhanced) == 0:
            cropped_enhanced = [utils.empty_pil_tensor()]

        if len(cropped_enhanced_alpha) == 0:
            cropped_enhanced_alpha = [utils.empty_pil_tensor()]

        if len(cnet_pil_list) == 0:
            cnet_pil_list = [utils.empty_pil_tensor()]

        return enhanced_img, cropped_enhanced, cropped_enhanced_alpha, mask, cnet_pil_list

    def doit(self, image, model, clip, vae, guide_size, guide_size_for, max_size, seed, steps, cfg, sampler_name, scheduler,
             positive, negative, denoise, feather, noise_mask, force_inpaint,
             bbox_threshold, bbox_dilation, bbox_crop_factor,
             sam_detection_hint, sam_dilation, sam_threshold, sam_bbox_expansion, sam_mask_hint_threshold,
             sam_mask_hint_use_negative, drop_size, bbox_detector, wildcard, cycle=1,
             sam_model_opt=None, segm_detector_opt=None, detailer_hook=None, inpaint_model=False, noise_mask_feather=0,
             scheduler_func_opt=None, tiled_encode=False, tiled_decode=False):

        result_img = None
        result_mask = None
        result_cropped_enhanced = []
        result_cropped_enhanced_alpha = []
        result_cnet_images = []

        if len(image) > 1:
            logging.warning("[Impact Pack] WARN: FaceDetailer is not a node designed for video detailing. If you intend to perform video detailing, please use Detailer For AnimateDiff.")

        for i, single_image in enumerate(image):
            enhanced_img, cropped_enhanced, cropped_enhanced_alpha, mask, cnet_pil_list = FaceDetailer.enhance_face(
                single_image.unsqueeze(0), model, clip, vae, guide_size, guide_size_for, max_size, seed + i, steps, cfg, sampler_name, scheduler,
                positive, negative, denoise, feather, noise_mask, force_inpaint,
                bbox_threshold, bbox_dilation, bbox_crop_factor,
                sam_detection_hint, sam_dilation, sam_threshold, sam_bbox_expansion, sam_mask_hint_threshold,
                sam_mask_hint_use_negative, drop_size, bbox_detector, segm_detector_opt, sam_model_opt, wildcard, detailer_hook,
                cycle=cycle, inpaint_model=inpaint_model, noise_mask_feather=noise_mask_feather, scheduler_func_opt=scheduler_func_opt,
                tiled_encode=tiled_encode, tiled_decode=tiled_decode)

            result_img = torch.cat((result_img, enhanced_img), dim=0) if result_img is not None else enhanced_img
            result_mask = torch.cat((result_mask, mask), dim=0) if result_mask is not None else mask
            result_cropped_enhanced.extend(cropped_enhanced)
            result_cropped_enhanced_alpha.extend(cropped_enhanced_alpha)
            result_cnet_images.extend(cnet_pil_list)

        pipe = (model, clip, vae, positive, negative, wildcard, bbox_detector, segm_detector_opt, sam_model_opt, detailer_hook, None, None, None, None)
        return result_img, result_cropped_enhanced, result_cropped_enhanced_alpha, result_mask, pipe, result_cnet_images
