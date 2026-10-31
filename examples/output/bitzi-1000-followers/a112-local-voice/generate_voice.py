import pathlib, soundfile as sf, torch, numpy as np, sys
sys.path.insert(0, '/app')
import server
server._ensure_perth_watermarker()
from chatterbox.models.tokenizers import tokenizer as tokenizer_module
# Use the already provisioned local tokenizer; this run must not access the Hub.
tokenizer_module.hf_hub_download = lambda repo_id, filename, cache_dir=None, **kwargs: str(pathlib.Path(cache_dir) / filename)
tokenizer_module.ChineseCangjieConverter._init_segmenter = lambda self: setattr(self, 'segmenter', None)
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
work=pathlib.Path('/work')
voice=ChatterboxMultilingualTTS.from_local('/models/voice',device='cuda')
reference=work/'bitzi-voice-reference.wav'
lines=[
 (1,"One thousand followers! Roland, we did it!"),
 (2,"Thank you, everyone! More confetti!"),
]
for index,text in lines:
 torch.manual_seed(771+index)
 with torch.inference_mode():
  audio=voice.generate(text,language_id='en',audio_prompt_path=str(reference),exaggeration=.60,cfg_weight=.35).detach().cpu().reshape(-1).numpy()
 sf.write(work/f'bitzi-line-{index}.wav',audio,voice.sr)
 print(index,round(len(audio)/voice.sr,2),voice.sr,text,flush=True)
