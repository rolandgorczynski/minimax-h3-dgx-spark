"""Image-reference sampling using the installed native ComfyUI FLUX.2 nodes."""
import torch
import comfy.utils
import comfy.samplers
from comfy_extras.nodes_flux import EmptyFlux2LatentImage, Flux2Scheduler
from comfy_extras.nodes_edit_model import ReferenceLatent
from comfy_extras.nodes_custom_sampler import BasicGuider, RandomNoise, SamplerCustomAdvanced


def prepare_reference(vae, image):
    height, width = image.shape[1:3]
    scale = min(1, 768/max(height, width))
    width = max(16, round(width*scale/16)*16)
    height = max(16, round(height*scale/16)*16)
    pixels = comfy.utils.common_upscale(image.movedim(-1, 1), width, height, 'lanczos', 'disabled').movedim(1, -1)
    with torch.inference_mode():
        return {'samples': vae.encode(pixels[:, :, :, :3])}


def generate_panel(model, clip, vae, reference_latent, text, seed):
    width, height = 1024, 704
    with torch.inference_mode():
        conditioning = clip.encode_from_tokens_scheduled(clip.tokenize(text))
        conditioning = ReferenceLatent.execute(conditioning, reference_latent)[0]
        guider = BasicGuider.execute(model, conditioning)[0]
        noise = RandomNoise.execute(seed)[0]
        latent = EmptyFlux2LatentImage.execute(width, height, 1)[0]
        sigmas = Flux2Scheduler.execute(4, width, height)[0]
        sampled = SamplerCustomAdvanced.execute(noise, guider, comfy.samplers.sampler_object('euler'), sigmas, latent)[0]
        return vae.decode(sampled['samples'])
