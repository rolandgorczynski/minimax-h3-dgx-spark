"""Whole-story planning with the existing Qwen3 text model inside ComfyUI."""
import hashlib
import json
import re


STYLES = {
    "Klassischer Comic": "European editorial comic illustration, confident ink outlines, muted colors, realistic expressive people.",
    "Großstadt-Noir (düster)": "Cinematic urban noir in a fictional metropolis, wet asphalt, cold blue and black, deep shadows, fog, hard beams of light, imposing tall buildings, realistic people. Sysop is a narrator silhouette in a dark coat. No superhero costumes or logos. No explicit violence.",
    "Ligne claire": "Franco-Belgian ligne claire comic, clean uniform ink lines, flat colors, precise architecture, readable compositions.",
    "Manga Schwarzweiß": "Black and white manga, expressive ink drawing, screentones, cinematic compositions, consistent realistic character proportions.",
    "Aquarell-Reportage": "Watercolor reportage comic, subtle ink contours, textured paper, restrained colors, realistic people, thoughtful journalistic mood.",
    'Graphic Novel realistisch': 'Realistic graphic novel illustration, cinematic framing, detailed textures, natural proportions, textured ink shading, restrained sophisticated colors, dramatic but plausible light.',
    'Holzschnitt / Linolschnitt': 'Expressive woodcut and linocut comic illustration, bold carved black shapes, strong black and white contrast, visible cut marks, simplified readable forms, restrained paper texture.',
    'Retro-Zeitungscomic': 'Vintage newspaper comic illustration, limited warm color palette, coarse halftone print texture, clear black ink outlines, expressive faces, readable classic staging. No printed lettering.',
    'Europäischer Abenteuercomic': 'European adventure comic illustration, lively controlled colors, precise detailed locations, clear consistent forms, crisp ink contours, dynamic readable cinematic staging.',
    'Science-Fiction / Cyberpunk': 'Science fiction cyberpunk comic illustration, luminous neon accents, blue and magenta palette, layered futuristic city architecture, technological details, atmospheric haze, realistic proportions.',
    'Warme Alltagsillustration': 'Warm intimate everyday-life comic illustration, soft natural light, muted warm colors, gentle ink contours, natural proportions, inviting lived-in environments, thoughtful quiet compositions.',
}

from pathlib import Path
for _style in json.loads(Path(__file__).with_name('style_catalog.json').read_text()):
    STYLES[_style['name']]=_style['prompt']


def source_hash(story, count, seed, style=""):
    return hashlib.sha256(json.dumps([story.strip(), count, seed], ensure_ascii=False).encode()).hexdigest()


def plan_matches(saved, story, count, seed):
    """Keep pre-update plans usable when their hash included the visual style."""
    fingerprints = {source_hash(story, count, seed)}
    for style in STYLES.values():
        fingerprints.add(hashlib.sha256(json.dumps(
            [story.strip(), count, seed, style], ensure_ascii=False).encode()).hexdigest())
    return isinstance(saved, dict) and saved.get('source_hash') in fingerprints


def read_plan(value, count):
    if isinstance(value, str):
        value = re.sub(r'<think>.*?</think>', '', value, flags=re.S).strip()
        start = value.find('[')
        if start < 0:
            raise ValueError('Das Sprachmodell hat keinen gültigen Szenenplan geliefert.')
        try:
            value = json.JSONDecoder().raw_decode(value[start:])[0]
        except ValueError as exc:
            raise ValueError('Der Szenenplan ist unvollständig. Bitte erneut planen.') from exc
    if not isinstance(value, list) or len(value) != count:
        raise ValueError(f'Der Plan muss genau {count} Kacheln enthalten.')
    scenes = []
    for i, scene in enumerate(value):
        if not isinstance(scene, dict) or not isinstance(scene.get('story'), str) or not scene['story'].strip():
            raise ValueError(f'Kachel {i+1}: Szenenbeschreibung fehlt.')
        dialog = scene.get('dialog', '')
        if not isinstance(dialog, str) or len(dialog) > 400 or len(scene['story']) > 4000:
            raise ValueError(f'Kachel {i+1}: Szenenbeschreibung oder Dialog zu lang.')
        result = {'story': scene['story'].strip(), 'dialog': dialog.strip()}
        if 'characters' in scene:
            ids = scene['characters']
            if not isinstance(ids, list) or len(ids)>8 or any(not isinstance(x,str) or not re.fullmatch(r'[a-f0-9]{32}',x) for x in ids):
                raise ValueError(f'Kachel {i+1}: Ungültige Figuren-Zuordnung.')
            result['characters'] = ids
        if 'bubbles' in scene:
            from .design import validate_bubbles
            result['bubbles'] = validate_bubbles(scene['bubbles'])
        if 'offscreen_speakers' in scene:
            from .design import validate_offscreen_speakers
            result['offscreen_speakers']=validate_offscreen_speakers(scene['offscreen_speakers'])
            if set(result['offscreen_speakers'])&set(result.get('characters',[])):raise ValueError('Sprecher nicht zugleich sichtbar und außerhalb des Bildes angeben.')
        if 'character_states' in scene:
            from .design import validate_character_states
            result['character_states']=validate_character_states(scene['character_states'])
        if 'lettering_draft' in scene:
            if type(scene['lettering_draft']) is not bool:raise ValueError('Ungültige Entwurfsmarkierung.')
            result['lettering_draft']=scene['lettering_draft']
        if 'canvas_size' in scene:
            from .design import validate_canvas_size
            result['canvas_size']=list(validate_canvas_size(scene['canvas_size']))
        if 'render_size' in scene:
            dims=scene['render_size']
            from .design import validate_render_size
            result['render_size']=list(validate_render_size(dims))
        scenes.append(result)
    return scenes


def source_sections(story, count):
    """Group consecutive paragraphs without dropping the article's ending."""
    units = [part.strip() for part in re.split(r'\n\s*\n', story.strip()) if part.strip()]
    if len(units) < count:
        units = [part.strip() for part in re.split(r'(?<=[.!?])\s+|\n+', story.strip()) if part.strip()]
    if len(units) < count:
        return []
    prefix = [0]
    for unit in units:
        prefix.append(prefix[-1] + len(unit))
    boundaries = [0]
    for i in range(1, count):
        candidates = range(boundaries[-1]+1, len(units)-(count-i)+1)
        boundaries.append(min(candidates, key=lambda index: abs(prefix[index]-prefix[-1]*i/count)))
    boundaries.append(len(units))
    return ['\n\n'.join(units[a:b]) for a, b in zip(boundaries, boundaries[1:])]


def plan_story(clip, story, count, seed, edited='', style='', cast=None):
    if not story.strip():
        raise ValueError('Bitte zuerst den Originalartikel oder die Gesamtgeschichte in das Artikelfeld einfügen. Figurenbeschreibungen ersetzen die Geschichte nicht.')
    if len(story) > 16000:
        raise ValueError('Die Gesamtgeschichte darf maximal 16000 Zeichen enthalten.')
    if type(count) is not int or count<1:
        raise ValueError('Bitte eine positive Kachelanzahl auswählen.')
    fingerprint = source_hash(story, count, seed, style)
    if edited.strip():
        try:
            saved = json.loads(edited)
            if plan_matches(saved, story, count, seed):
                return read_plan(saved['scenes'], count), fingerprint
        except (ValueError, KeyError, AttributeError):
            # Invalid edits must not silently discard a user's work.
            raise ValueError('Der bearbeitete Szenenplan ist ungültig. Bitte korrigieren oder neu planen.')
    # Allocate the whole source before asking for visuals, so a long opening
    # cannot consume every panel and leave the end of the article uncovered.
    sections = source_sections(story, count)
    source = '\n\n'.join(f'Kachel {i+1} – Quellabschnitt:\n{text}' for i, text in enumerate(sections)) if sections else story.strip()
    cast_instructions = ''
    if cast:
        from .characters import character_prompt
        cast_instructions = 'REUSABLE CHARACTER PROFILES (preserve these names and identities in every appearance; aliases refer to the same person):\n'+'\n'.join(character_prompt(c) for c in cast)
    if cast is None:
        narrator_rule = 'Include the narrator Sysop exactly once in EVERY panel. He observes from the shadows.'
        narrator_appearance = 'Sysop has shoulder-length dark hair and a beard; in noir he wears a dark coat.'
    else:
        from .characters import is_sysop
        selected_sysop = next((c for c in cast if is_sysop(c)),None)
        narrator_rule = (f'Use {selected_sysop["name"]} as the observing narrator, using the saved character profile.' if selected_sysop else 'Do not add Sysop or an extra narrator character. Narration is a text box.')
        narrator_appearance = 'Use the saved character profiles for every selected person, including any narrator.'
    prompt = f'''Create a visual comic storyboard from the source article, in the article's language.
Return ONLY a JSON array of exactly {count} objects with keys "story", "dialog" and "bubbles".
{('Each numbered source block maps to exactly ONE panel in the same order. Include the LAST block.' if sections else 'Cover the entire article including the ending.')}
"story": a concrete camera composition, visible setting, people and objects. Maximum 350 characters. {narrator_rule} An observing narrator never participates in reported events. Do not copy article sentences into story. Use symbolic scenes for institutions and unknown events.
"bubbles": a list of attributed spoken lines ONLY if explicitly present in the source: {{"speaker":"character name", "text":"exact spoken words", "expression":"normal"}}. Otherwise an empty list. Do not invent or paraphrase spoken dialogue.
"dialog": a separate factual narrator caption, maximum 220 characters. Preserve attribution, uncertainty and presumption of innocence. Never label a suspect as a convicted perpetrator. Preserve questions as questions. Invent no actions, motives or quotations. Article-relative dates remain relative.
Example format: [{{"story":"Nasse Straße im kalten blauen Licht. Ein junger Mann trägt einen Einkaufsbeutel.","dialog":"Er war auf dem Heimweg vom Supermarkt."}}]
Depict violence indirectly with an empty street, shadows or a closed hospital door. No blood, wounds or visible attack. No superhero costumes or logos.
CONSISTENT ART STYLE: {style or STYLES["Klassischer Comic"]}
{narrator_appearance}
{cast_instructions}
SOURCE BLOCKS:
{source}
Output all {count} visual panels as JSON now. /no_think'''
    from comfy_extras.nodes_textgen import TextGenerate
    sampling = {'sampling_mode': 'on', 'temperature': 0.2, 'top_k': 40, 'top_p': 0.9,
                'min_p': 0.05, 'repetition_penalty': 1.05, 'seed': seed}
    length = min(4096, count*320+300)
    response = TextGenerate.execute(clip, prompt, length, sampling, thinking=False)[0]
    try:
        scenes = read_plan(response, count)
    except ValueError:
        repair = f'Return only a valid JSON array with exactly {count} objects, each with string keys story and dialog. Fix this comic plan without changing the plot or language:\n{response}\n/no_think'
        response = TextGenerate.execute(clip, repair, length, {'sampling_mode': 'off'}, thinking=False)[0]
        scenes = read_plan(response, count)
    from .design import validate_bubbles
    from .characters import explicit_speech, canonical_speaker
    for i,scene in enumerate(scenes):
        quoted = explicit_speech(sections[i] if sections else story) if sections or count==1 else []
        # Explicitly attributed source quotations take precedence over model output.
        if quoted:
            scene['bubbles'] = validate_bubbles(quoted)
        scene.setdefault('bubbles', [])
        for bubble in scene['bubbles']:
            bubble['speaker'] = canonical_speaker(bubble['speaker'],cast or [])
    return scenes, fingerprint
