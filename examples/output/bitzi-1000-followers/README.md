# Bitzi celebrates 1,000 followers

Two 10.125-second versions are provided for a direct listening comparison. Both use the same 243 video frames, the same title, English captions, watermark, H3-generated music and effects, and conservative final loudness mastering.

## Versions

- [Baseline: MiniMax H3 native voice](first-h3/bitzi_1000_followers_first_h3.mp4) — H3 generates the picture and its native joint soundtrack.
- [A-112: local reference voice](a112-local-voice/bitzi_1000_followers_a112_local_voice.mp4) — same picture and soundtrack bed; the Bitzi speech is replaced with locally generated Chatterbox Multilingual V3 speech conditioned on the saved Bitzi voice reference.

The 243 video-frame hashes match exactly between the two outputs. Only the audio differs. The first clip is Telegram message 171; the local-reference version is message 172 in the private comparison group.

## Production inputs

- [Keyframe](first-h3/scene1.png), generated from Roland's supplied photo and the canonical Bitzi avatar reference.
- [Thank-you poster](first-h3/1000-followers-poster.png).
- [ComfyUI API workflow](first-h3/workflow_api.json), [English captions](first-h3/subtitles.srt), and [baseline production notes](first-h3/story.md).
- [A-112 voice-generation and mix notes](a112-local-voice/README.md), with scripts and the archived reference audio.

The local voice version uses a saved synthetic Bitzi reference, not a human voice clone. On this ARM64 runtime the optional Perth watermarker class is unavailable; the installed project's documented fallback passes audio through without adding that watermark. Model weights are not copied into this repository.
