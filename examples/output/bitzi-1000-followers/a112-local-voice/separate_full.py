import sys, soundfile as sf
sys.path.insert(0, '/app')
from speech_separation import BanditEngine
source, rate = sf.read('/work/original.wav', dtype='float32', always_2d=True)
engine = BanditEngine('/models')
try:
    speech = engine.estimate(source)
finally:
    engine.close()
if speech.shape != source.shape:
    raise SystemExit(f'shape mismatch: {source.shape} != {speech.shape}')
sf.write('/work/vocals.wav', speech, rate, subtype='FLOAT')
print(f'Extracted speech stem: {len(speech)/rate:.2f}s at {rate} Hz', flush=True)
