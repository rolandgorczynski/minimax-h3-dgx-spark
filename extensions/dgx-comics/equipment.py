"""Ein einzelnes Schwert behält Identität und genau einen physischen Zustand."""
import re

POSITIONS={'in der Scheide','gezogen','rechte Hand','linke Hand','am Boden','nicht sichtbar','nicht festgelegt'}
DETAILS={
 'in der Scheide':'Genau ein Schwert insgesamt: vollständig in der Scheide; genau ein Griff an der Scheide. Kein zusätzliches Schwert in den Händen.',
 'gezogen':'Genau ein Schwert insgesamt: aus der Scheide gezogen und in der Hand. Die Schwertscheide ist leer, ohne Klinge und ohne zweiten Schwertgriff. Kein weiteres Schwert am Gürtel oder Rücken.',
 'rechte Hand':'Genau ein Schwert insgesamt: in der rechten Hand. Linke Hand ohne weiteres Schwert. Die Schwertscheide ist leer und zeigt keinen Schwertgriff. Kein weiteres Schwert am Gürtel oder Rücken.',
 'linke Hand':'Genau ein Schwert insgesamt: in der linken Hand. Rechte Hand ohne weiteres Schwert. Die Schwertscheide ist leer und zeigt keinen Schwertgriff. Kein weiteres Schwert am Gürtel oder Rücken.',
 'am Boden':'Das einzige Schwert liegt am Boden. Kein Schwert mehr in den Händen. Die Schwertscheide ist leer und zeigt keinen Schwertgriff. Kein zusätzliches Schwert am Gürtel oder Rücken.',
 'nicht sichtbar':'Das einzige Schwert ist nicht sichtbar. Kein zusätzliches Schwert erfinden; Verdeckung ist kein Besitzwechsel.',
 'nicht festgelegt':'Genau ein einziges physisches Schwert insgesamt. Hand, Scheide und Boden sind mögliche Aufenthaltsorte desselben Gegenstands, niemals zusätzliche Exemplare.'}


def single_sword(character):
    text=character.get('story_outfit') or character.get('outfit','')
    # Nur ausdrücklich ein einzelnes Schwert; keine pauschale Vorgabe für Doppelbewaffnung.
    counts=re.findall(r'\b(kein(?:e[nmrs]?)?|ein(?:e[nmrs]?)?|[0-9]+|zwei|drei|vier)\s+(?:(?!(?:ein(?:e[nmrs]?)?|kein(?:e[nmrs]?)?|zwei|drei|vier|\d+|und)\b)[\w-]+\s+){0,3}Schwert(?:er[n]?)?\b',text,re.I)
    def count(word):return 0 if word.lower().startswith('kein') else 1 if word.lower().startswith('ein') else {'zwei':2,'drei':3,'vier':4}.get(word.lower(),int(word) if word.isdigit() else -1)
    return bool(counts) and {count(v) for v in counts}=={1}


def initial(cast):
    return {c['id']:{'sword_position':'in der Scheide' if re.search(r'Scheide|Gürtel|an (?:seiner|der) Seite',c.get('story_outfit') or c.get('outfit',''),re.I) else 'nicht festgelegt'} for c in cast if single_sword(c)}


def instruction(character):
    if not single_sword(character):return ''
    return (character['name']+': exactly ONE physical sword in total. Drawing the sword is a change of location of that SAME sword, never a new copy. '
        'When drawn, the scabbard is EMPTY: no blade and NO SECOND HILT at the belt or back. When sheathed, no sword remains in a hand. '
        'When laid down, the same sword is on the ground, not also in a hand or scabbard. '
        'Current scene and explicit physical state override default outfit placement. Reference portraits do not add equipment. Never multiply the sword, its blade, or its hilt.')
