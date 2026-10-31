# 1,000 Followers — baseline H3 version

A short celebration starring Bitzi and Roland. Bitzi hears that the channel has reached one thousand followers, bounces around in delight, thanks everyone, and triggers one last burst of confetti. Roland appears photorealistically from his supplied portrait and answers with a grateful smile and hand over his heart; no synthetic voice is assigned to him.

Dialogue intended for Bitzi:

“One thousand followers! Roland, we did it!”

“Thank you, everyone! More confetti!”

## Baseline production

- Video model: MiniMax H3, run locally in ComfyUI on the DGX Spark.
- Task: image-to-video, one continuous shot, 480 × 864, 24 fps, 243 frames (10.125 seconds), 20 Euler steps, seed 2026103117.
- Audio: H3 native joint audio. The generated FLAC is 7.3 seconds; the final mux pads the track to the picture duration after a conservative loudness pass. No separate TTS voice or additional music model is used in this baseline.
- Keyframe: generated with OpenAI image generation from Roland’s supplied photo and the canonical Bitzi channel-avatar reference. This is intentionally recorded because it is not a fully local image-generation path.
- Final export: 720 × 1280, H.264/AAC, English subtitles, title card text, and Roland Gorczynski / bits.gorczynski.online watermark.

This is the control version for an A/B comparison with an A-112-inspired local-voice version. It does not claim to implement the report’s recommended local TTS, voice reference, or 2–5-second shot assembly. The actual spoken words should be checked by listening because the H3 script is a prompt, not a guaranteed transcript.
