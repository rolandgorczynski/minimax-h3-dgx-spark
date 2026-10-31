from pathlib import Path
import numpy as np
import soundfile as sf
import librosa

work=Path('/work')
rate=44100
original,sr=sf.read(work/'original.wav',dtype='float32',always_2d=True)
vocals,vr=sf.read(work/'vocals.wav',dtype='float32',always_2d=True)
if sr!=rate or vr!=rate or original.shape!=vocals.shape:
    raise SystemExit(f'audio mismatch: original={original.shape}@{sr}, vocals={vocals.shape}@{vr}')
# Exact same source music/SFX as the baseline; only the Bitzi dialogue is replaced.
# The first local TTS line is lightly time-stretched to fit the baseline cue.
lines=[(0.50,3.70,1),(4.15,7.25,2)]
converted=np.zeros_like(vocals)
for start,end,index in lines:
    a,b=int(start*rate),min(len(converted),int(end*rate))
    n=min(int(.08*rate),(b-a)//4)
    voice,sample_rate=sf.read(work/f'bitzi-line-{index}-processed.wav',dtype='float32')
    if sample_rate!=24000:
        voice=librosa.resample(voice,orig_sr=sample_rate,target_sr=24000)
    available=(end-start-.10)
    if len(voice)/24000>available:
        voice=librosa.effects.time_stretch(voice,rate=(len(voice)/24000)/available)
    voice=librosa.resample(voice,orig_sr=24000,target_sr=rate)
    voice=voice[:max(0,b-a-2*n)]
    fade=min(int(.035*rate),len(voice)//4)
    if fade:
        env=np.ones(len(voice),dtype='float32')
        env[:fade]=np.linspace(0,1,fade)
        env[-fade:]=np.linspace(1,0,fade)
        voice*=env
    offset=a+n
    stop=min(offset+len(voice),b-n)
    converted[offset:stop]+=voice[:stop-offset,None]*.55
    print(f'line {index}: inserted {len(voice)/rate:.2f}s at {offset/rate:.2f}s',flush=True)
bed=original-vocals
# Suppress the imperfect H3 speech estimate under dialogue. Keep the H3 music/SFX bed
# between lines and at the opening/closing, with short fades at each duck boundary.
for start,end in ((0.38,3.84),(4.03,7.40)):
    a,b=int(start*rate),min(len(bed),int(end*rate))
    fade=int(.08*rate)
    bed[a:b]=0
    if fade:
        left=max(0,a-fade); right=min(len(bed),b+fade)
        if a>left:
            bed[left:a]*=np.linspace(1,0,a-left,endpoint=False,dtype='float32')[:,None]
        if right>b:
            bed[b:right]*=np.linspace(0,1,right-b,endpoint=False,dtype='float32')[:,None]
mix=bed+converted
peak=float(np.max(np.abs(mix)))
if not np.isfinite(mix).all():
    raise SystemExit('non-finite sample in final mix')
if peak>.98:
    mix*=.98/peak
sf.write(work/'a112_mixed_single_voice.wav',mix,rate,subtype='PCM_24')
print(f'mix: {len(mix)/rate:.2f}s, peak={min(peak,.98):.4f}',flush=True)
