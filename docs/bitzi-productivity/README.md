# Bitzi: The Productivity Revolution

An English, 60-second vertical office-comedy short based on `film.txt` in the x-generator repository. The story follows the brief: Bitzi removes the employees, then the customers, and proudly leaves the productivity dashboard at 100%.

## Production

Six individually illustrated scene keyframes preserve Bitzi's canonical identity. They were created against `characters/bitzi/images/bitzi-avatar-reference.png`; the finished PNGs live in `examples/input/bitzi-productivity/`. MiniMax H3 runs locally in ComfyUI and generates each scene's motion, dialogue, music and effects. The assembler joins the six clips, adds English captions, normalizes and limits audio, and burns in the Roland Gorczynski / bits.gorczynski.online signature.

```bash
python3 scripts/run_bitzi_productivity.py
```

The assembled film is written to `/home/jee/docker/minimax-h3-data/output/x-generator/bitzi-productivity/bitzi_the_productivity_revolution_60s.mp4`.

The generated spoken dialogue can vary slightly from the script. Listen to the finished mix before publishing; captions follow the approved wording.
