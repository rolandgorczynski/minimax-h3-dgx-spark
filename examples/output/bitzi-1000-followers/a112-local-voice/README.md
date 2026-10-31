# 1,000 Followers — A-112 local-voice comparison

This version reuses the exact baseline video frames and shot timing. It replaces Bitzi's H3-native speech with a locally generated, reference-conditioned Chatterbox Multilingual V3 voice while retaining the same H3 music and sound effects.

## A-112 elements applied

- Local Chatterbox Multilingual V3, MIT weights, with the existing 3-second Bitzi reference derived from a prior H3 Bitzi performance. The same reference is used for both lines; fixed seeds and settings (`exaggeration=0.60`, `cfg_weight=0.35`) make this run reproducible.
- BandIt speech estimate isolates the existing speech so it can be replaced while keeping H3's generated music/SFX bed. The local separator runs offline; its model directory is read-only.
- Exact scripted English dialogue is generated line by line. The local clips are placed into the same 10.125-second picture timeline.
- Conservative final loudness target is −16 LUFS and −1.5 dBTP, with a 48 kHz stereo AAC export. H3's integrated soundtrack is not passed through speech-only filters.

The Perth audio-watermarker extension is unavailable in this ARM64 runtime. The installed `dgx-spark-tts` fallback reports this and uses a pass-through, as its existing local implementation does. No Chatterbox voice watermark is applied in this setup.

## Dialogue

“One thousand followers! Roland, we did it!”

“Thank you, everyone! More confetti!”

The comparison is for voice texture and clarity. Both videos use the same generated picture, title, subtitle style, music/SFX source, watermark, and duration. They are not yet a listener-approved final character voice.
