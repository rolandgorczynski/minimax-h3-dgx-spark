# BITZI – The Cursed Halloween Party

Episode 03. The screenplay is in `story.md`; the six consistent cast keyframes are in `examples/input/bitzi-cursed-halloween-party/`.

Render through the local ComfyUI MiniMax H3 service:

```sh
python scripts/run_bitzi_cursed_halloween_party.py
```

This submits six scenes in sequence using the shared `CAST_LOCK`, then assembles them with German subtitles, a restrained audio mix, the recurring credit watermark and a two-second end card. The final MP4 is written to `/home/jee/docker/minimax-h3-data/output/x-generator/bitzi-cursed-halloween-party/bitzi_cursed_halloween_party.mp4`.

Scene-specific dialogue, visual direction and render wiring live in `scripts/submit_bitzi_cursed_halloween_party.py`. The assembly and captions are in `scripts/assemble_bitzi_cursed_halloween_party.py`. Character reference sheets remain the source of truth for Bitzi, the Linux admin and the CEO; no voice cloning is used.
