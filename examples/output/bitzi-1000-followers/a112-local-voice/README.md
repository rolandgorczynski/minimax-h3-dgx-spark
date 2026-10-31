# 1,000 Followers — A-112 local-voice comparison

This corrected version reuses the exact baseline video frames and shot timing. Bitzi's dialogue uses a locally generated, reference-conditioned Chatterbox Multilingual V3 voice. H3 music and effects remain in the opening, pause between lines, and ending. The imperfectly separated H3 dialogue is fully muted during both spoken lines, so only one voice is heard there.

## A-112 elements applied

- Local Chatterbox Multilingual V3, MIT weights, with the existing 3-second synthetic Bitzi reference derived from a prior H3 Bitzi performance. Both lines use the same reference, fixed seeds, `exaggeration=0.60`, and `cfg_weight=0.35`.
- BandIt estimates the original speech. The H3 mix is muted through each dialogue window to prevent residual speech from leaking under the replacement voice; H3 ambience/music/SFX are retained between the lines and around the ending.
- Exact scripted English dialogue is generated line by line and placed on the same 10.125-second picture timeline.
- The reference voice is filtered gently with an 80 Hz high-pass, light de-essing, and 2:1 compression. Final mastering targets −18 LUFS and −2 dBTP; export is 48 kHz stereo AAC.

The Perth audio-watermarker extension is unavailable in this ARM64 runtime. The installed `dgx-spark-tts` fallback reports this and uses a pass-through, as its existing local implementation does. No Chatterbox voice watermark is applied in this setup.

## Dialogue

“One thousand followers! Roland, we did it!”

“Thank you, everyone! More confetti!”

The corrected comparison differs from the baseline only in audio. The earlier A/B upload had residual H3 speech under the local voice; the corrected file is `bitzi_1000_followers_a112_local_voice_single.mp4`. It is not yet a listener-approved final character voice.
