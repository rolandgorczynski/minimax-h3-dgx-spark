# Bitzi + Linux-Admin: reproduzierbare Grundlage

Diese Notizen trennen Bild- und Videogenerierung. Die Comic-Varianten ab `comic-v1` laufen lokal über ComfyUI unter `http://192.168.1.224:8188`. Der allererste fotorealistische Probe-Keyframe wurde versehentlich mit dem integrierten, externen Bildgenerator erstellt statt mit lokalem ComfyUI; er ist nicht die neue Serienreferenz. Das Originalfoto liegt nicht im Repository. Alle abgeleiteten Comic-Referenzen und die weiteren Filmvarianten entstehen lokal.

## Comic-Avatar des Linux-Admins

- ComfyUI-Knoten: `DGXComicPortrait` aus `dgx-comics/automation.py`.
- Modell: `flux-2-klein-9b-bf16.safetensors`, `qwen_3_8b.safetensors` mit Typ `flux2`, `flux2-vae.safetensors`.
- Sampler: lokaler `generate_panel`-Pfad; FLUX.2-Scheduler mit 4 Schritten und Euler-Sampler.
- Seed: `2026103112`.
- Referenz: lokales Foto, vor dem VAE-Encoding auf maximal 768 Pixel Kantenlänge verkleinert.
- Bildbeschreibung: „An adult male Linux administrator inspired by the supplied portrait: short brown hair with a receding hairline, dark rectangular glasses, broad friendly face, dark navy blazer and pale blue shirt. Calm, capable expression and a warm small smile showing a little clean light-ivory upper teeth. Keep his recognizable facial structure and glasses, but translate fully into a stylized comic character.“
- Stil: „Polished hand-drawn 3D comic illustration, clear inked contours, simplified rounded shapes, expressive face, rich but restrained colors, soft cel shading, warm approachable animation-series design, obviously illustrated and never photorealistic. Teal and navy palette. Neutral pale teal backdrop, portrait only.“
- Ergebnis: [`../../characters/linux-admin/images/linux-admin-avatar-comic-v1.png`](../../characters/linux-admin/images/linux-admin-avatar-comic-v1.png).

## Comic-Schlüsselbild

- ComfyUI-Knoten: `DGXComicStudio`, ein Panel, Stil `Cartoon mit runden Formen`.
- Dieselben drei FLUX.2/Qwen3/VAE-Modelle wie beim Avatar.
- Seed: `2026103113`; Rendergröße und Leinwand: `768 × 1344`.
- Referenzen in der Besetzung: Admin-Comic-Avatar zuerst, Bitzis Kanal-Avatar als zweite Referenz. Comic-Stil und Szenenbeschreibung stehen im API-Workflow.
- Ergebnis: [`../../examples/input/bitzi-admin-photo-proof/scene1-comic.png`](../../examples/input/bitzi-admin-photo-proof/scene1-comic.png).

## MiniMax-H3-Clip

- API-Workflow: [`../../examples/api/bitzi_admin_photo_comic_v1.json`](../../examples/api/bitzi_admin_photo_comic_v1.json).
- Modelle: `minimax_h3_fl2va_pruned_int8_convrot.safetensors`, `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`, `minimax_h3_video_vae_fp16.safetensors`, `minimax_h3_audio_vae_fp32.safetensors`.
- Ausgabe: `480 × 864`, 24 Bilder/Sekunde, 243 Frames = 10,125 Sekunden.
- Sampling: 20 Schritte, CFG 1.0, Euler, Scheduler `simple`, Denoise 1.0, Video-Sigma-Shift 12, Audio-Sigma-Shift 3.
- Seed: `2026103114`.
- H3 speichert Video und Audio getrennt. Beim Mux wird die Audiospur um 6 dB abgesenkt, weil die rohe Spur bis 0 dBFS reicht.

## Vergleichsregel für weitere Tests

Für einen aussagekräftigen A/B-Vergleich dieselbe Referenz, denselben Prompt, dieselben Seeds und dieselben Modellparameter beibehalten. Pro Test genau eine Einstellung ändern und die Variante im Namen dokumentieren. Die erste realistische Fassung und `comic-v1` unterscheiden sich absichtlich bei Referenzbild, Stil und Seed; sie sind daher ein Stilwechsel, kein kontrollierter Einzelparameter-Vergleich.

## Variante comic-v2-gray (vor dem Videorender)

- Nutzerkorrektur: Haare grau; Ton soll frei von scharfen Artefakten und unangenehmen Spitzen sein.
- Avatar und Schlüsselbild mit dem lokalen ComfyUI erstellt; kein externer Bildgenerator.
- Avatar-Seed `2026103115`, `DGXComicPortrait`; identische FLUX.2/Qwen3/VAE-Grundlage und 4-Schritt-Euler-Sampler wie v1.
- Schlüsselbild-Seed `2026103116`, `DGXComicStudio`, Stil `Cartoon mit runden Formen`, ein Panel, `768 × 1344`; Admin-Avatar zuerst, Bitzi-Avatar als zweite Referenz.
- Schlüsselbild: [`../../examples/input/bitzi-admin-photo-proof/scene1-comic-gray-v2.png`](../../examples/input/bitzi-admin-photo-proof/scene1-comic-gray-v2.png).
- Der Ton aus `comic-v1` wurde vom Nutzer als scharf, schmerzhaft und künstlich klingend bewertet; ihn nur leiser zu machen genügt nicht. Die nächste Fassung bekommt eine neu erzeugte lokale Sprach-/Musikspur und einen vorsichtigen Master. Nutzer sucht zusätzlich ein Klangbeispiel als Geschmacksreferenz.

Schlüsselbild-Prompt für `comic-v2-gray`: „Vertical medium shot in a softly lit modern server room. Exactly two characters appear once: the gray-haired Linux administrator from reference image 1 sits at a console looking at the process monitor; face fully visible, a calm small speaking smile with naturally light ivory teeth, dark rectangular glasses, navy blazer and pale blue shirt. Bitzi from reference image 2 floats beside the display and keeps the exact rounded turquoise chip mascot design. Abstract colored process rows only on screen, no readable text. Clearly illustrated comic style with confident ink contours and soft cel shading; not photorealistic. No title, no lettering, no speech balloons, no watermark.“
