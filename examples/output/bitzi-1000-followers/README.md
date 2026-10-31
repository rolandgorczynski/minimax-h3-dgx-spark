# Bitzi celebrates 1,000 followers

Two 10.125-second versions are available for a direct listening comparison. Both use the same 243 video frames, title, English captions, watermark and visual timing.

## Versions

- [Baseline: MiniMax H3 native voice](first-h3/bitzi_1000_followers_first_h3.mp4) — H3 generates the picture and native soundtrack.
- [A-112: local reference voice, single voice](a112-local-voice/bitzi_1000_followers_a112_local_voice_single.mp4) — same picture; Bitzi's speech uses a saved-reference Chatterbox voice. H3 music and effects remain in the gaps, while the mixed H3 soundtrack is muted during dialogue to prevent voice leakage.

The video-frame hashes match exactly. Telegram message 171 is the baseline. Message 172 now contains the corrected single-voice comparison; it replaced the earlier rough A/B mix in place.

## Production inputs

- [Keyframe](first-h3/scene1.png), generated from Roland's supplied photo and the canonical Bitzi avatar reference.
- [Thank-you poster](first-h3/1000-followers-poster.png).
- [ComfyUI API workflow](first-h3/workflow_api.json), [English captions](first-h3/subtitles.srt), and [baseline production notes](first-h3/story.md).
- [A-112 voice-generation and mix notes](a112-local-voice/README.md), scripts and archived reference audio.

The local voice uses a saved synthetic Bitzi reference, not a human voice clone. On this ARM64 runtime the optional Perth watermarker class is unavailable; the installed project's documented fallback passes audio through without adding that watermark. Model weights are not copied into this repository.
