"""Native ComfyUI FLUX.2 generation: no HTTP services or API credentials."""

def generate(model, clip, vae, description, seed, width=1792, height=1024):
    import torch
    import comfy.samplers
    from comfy_extras.nodes_flux import EmptyFlux2LatentImage, Flux2Scheduler
    from comfy_extras.nodes_custom_sampler import BasicGuider, RandomNoise, SamplerCustomAdvanced
    if any(value is None for value in (model, clip, vae)):
        raise ValueError('Podłącz lokalne węzły MODEL, CLIP i VAE. Otwórz aktualny workflow z folderu Plakaty.')
    text = description.strip() + '\nEditorial photograph, no text, no letters, no logos, wide composition.'
    with torch.inference_mode():
        conditioning = clip.encode_from_tokens_scheduled(clip.tokenize(text))
        latent = EmptyFlux2LatentImage.execute(width, height, 1)[0]
        sigmas = Flux2Scheduler.execute(4, width, height)[0]
        guider = BasicGuider.execute(model, conditioning)[0]
        noise = RandomNoise.execute(seed)[0]
        sampler = comfy.samplers.sampler_object('euler')
        sampled = SamplerCustomAdvanced.execute(noise, guider, sampler, sigmas, latent)[0]
        return vae.decode(sampled['samples'])
