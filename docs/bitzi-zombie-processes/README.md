# Bitzi: The Zombie Processes

Episode 02 of the Halloween run, based on `storys/BITZI/halloween/2026-10-31.md` in the X-Generator repository. Spoken dialogue is English; subtitles are German. The six scene keyframes use the Ghost in the Server cast reference, with the recurring character lock applied to every independently generated MiniMax H3 segment.

## Production

```bash
python3 scripts/run_bitzi_zombie_processes.py
```

MiniMax H3 runs locally in ComfyUI. The runner submits one segment at a time, waits for it to finish, and assembles the six clips with German captions, a safe audio mix, the signature, and an ending card.

Output: `/home/jee/docker/minimax-h3-data/output/x-generator/bitzi-zombie-processes/bitzi_zombie_processes_63s.mp4`

The technical explanation follows Linux process semantics: a zombie has already exited; its parent has not yet collected its exit status. Killing the parent is Bitzi's deliberately wrong comic solution. The restarted service recreates the bug by spawning a child without collecting that status.

MiniMax H3 generates each segment separately. The same canonical visual and voice descriptions are repeated in every prompt, but text alone cannot guarantee identical generated voices across clips. Check the final dialogue and audio before publishing.
