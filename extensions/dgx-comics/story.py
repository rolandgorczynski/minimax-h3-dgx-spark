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
}


def source_hash(story, count, seed, style=""):
    return hashlib.sha256(json.dumps([story.strip(), count, seed] + ([style] if style else []), ensure_ascii=False).encode()).hexdigest()


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
        scenes.append({'story': scene['story'].strip(), 'dialog': dialog.strip()})
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


def plan_story(clip, story, count, seed, edited='', style=''):
    if not story.strip() or len(story) > 16000 or not 1 <= count <= 12:
        raise ValueError('Bitte eine Gesamtgeschichte mit 1–16000 Zeichen und 1–12 Kacheln angeben.')
    fingerprint = source_hash(story, count, seed, style)
    if edited.strip():
        try:
            saved = json.loads(edited)
            if saved.get('source_hash') == fingerprint:
                return read_plan(saved['scenes'], count), fingerprint
        except (ValueError, KeyError, AttributeError):
            # Invalid edits must not silently discard a user's work.
            raise ValueError('Der bearbeitete Szenenplan ist ungültig. Bitte korrigieren oder neu planen.')
    # Allocate the whole source before asking for visuals, so a long opening
    # cannot consume every panel and leave the end of the article uncovered.
    sections = source_sections(story, count)
    source = '\n\n'.join(f'Kachel {i+1} – Quellabschnitt:\n{text}' for i, text in enumerate(sections)) if sections else story.strip()
    prompt = f'''Create a visual comic storyboard from the source article, in the article's language.
Return ONLY a JSON array of exactly {count} objects with keys "story" and "dialog".
{('Each numbered source block maps to exactly ONE panel in the same order. Include the LAST block.' if sections else 'Cover the entire article including the ending.')}
"story": a concrete camera composition, visible setting, people and objects. Maximum 350 characters. Include the narrator Sysop exactly once in EVERY panel. He observes from the shadows, never participates in the reported events. Do not copy article sentences into story. Use symbolic scenes for institutions and unknown events.
"dialog": a factual narrator caption, maximum 220 characters. Preserve attribution, uncertainty and presumption of innocence. Never label a suspect as a convicted perpetrator. Preserve questions as questions. Invent no actions, motives or quotations. Article-relative dates remain relative.
Example format: [{{"story":"Nasse Straße im kalten blauen Licht. Ein junger Mann trägt einen Einkaufsbeutel. Sysop beobachtet als Silhouette im dunklen Mantel vom Hintergrund aus.","dialog":"Er war auf dem Heimweg vom Supermarkt."}}]
Depict violence indirectly with an empty street, shadows or a closed hospital door. No blood, wounds or visible attack. No superhero costumes or logos.
CONSISTENT ART STYLE: {style or STYLES["Klassischer Comic"]}
Sysop has shoulder-length dark hair and a beard; in noir he wears a dark coat.
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
    return scenes, fingerprint
