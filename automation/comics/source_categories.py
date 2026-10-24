"""Quellen ohne Modellaufruf einordnen; gespeicherte Zuordnungen haben Vorrang."""
import re

CATEGORIES=(
    'Heldensagen und Mythen','Märchen und Verwandlungen','Geister und Spuk',
    'Drachen und Ungeheuer','Schätze und verborgene Orte','Teufel und Zauberei',
    'Heilige und Legenden','Historische Sagen','Abenteuer und Entdeckungen',
    'Fabeln und Tiergeschichten','Liebe und Treue','Regionale Sagen','Eigene Vorlagen',
)
# Bekannte redigierte Stoffe lassen sich genauer als nur über Titelwörter zuordnen.
OVERRIDES={
    'kleiner-prinz':'Märchen und Verwandlungen',
    'bremer-stadtmusikanten':'Fabeln und Tiergeschichten',
    'weihnachtsgeschichte':'Geister und Spuk',
    'comic-quellen-2-rattenfaenger':'Teufel und Zauberei',
    'comic-quellen-5-zeitmaschine':'Abenteuer und Entdeckungen',
    'comic-quellen-5-rikkitikkitavi':'Fabeln und Tiergeschichten',
    'comic-quellen-5-sleepy-hollow':'Geister und Spuk',
    'comic-quellen-5-geheimer-garten':'Abenteuer und Entdeckungen',
    'comic-quellen-5-zauberer-oz':'Märchen und Verwandlungen',
}
RULES=[
    ('Drachen und Ungeheuer',r'drach|lindwurm|ungeheuer|greif(?:en|\b)|minotaur'),
    ('Geister und Spuk',r'geist(?:er|es|\b)|gespenst|spuk|wiedergäng|kopflose|ohne kopf|nachtjäger|wilde.*jagd|todten|toten|tänzer|schatten|wehklag|weisse frau|weiße frau|nachtvolk|schrettele'),
    ('Teufel und Zauberei',r'teufel|satan|hex|zauber|faust|verwünsch|bann|verflucht'),
    ('Schätze und verborgene Orte',r'schatz|schätze|gold|silber|edelstein|diamant|verborgen|versunken|springwurzel|wünschelrut'),
    ('Heilige und Legenden',r'\bsankt\b|\bst\.\s|heilig|gottes|maria|madonna|christ|engel|wunder|kloster|kapelle|mönch|nonne|kreuz|kirche|bischof|papst|pilger'),
    ('Liebe und Treue',r'braut|bräut|hochzeit|verlob|liebe|geliebt|treue|treuen|jungfrau'),
    ('Historische Sagen',r'kaiser|könig|herzog|graf|ritter|schlacht|krieg|heer|belager|wallenstein|karls|karl der|friedrich|heinrich|bismarck'),
    ('Fabeln und Tiergeschichten',r'\bfuchs|\bwolf|\blöwe|\bmaus|\bmäuse|\brabe|\bstorch|\besel|\bziege|\bhahn|\bhund|\bschlange'),
]


def collection(source):
    ident=source.get('id','');creator=source.get('creator','').casefold()
    if ident.startswith('bechstein-sagen-'):return 'Bechstein – Deutsches Sagenbuch'
    if ident.startswith('heldensagen-'):return 'Mittelalterliche Heldensagen'
    if ident.startswith('comic-quellen-2-') and any(x in creator for x in ('snorri','simrock')):return 'Nordische Mythen'
    if 'bulfinch' in creator:return 'Antike Mythen'
    if 'grimm' in creator:
        return 'Grimm – Sagen' if 'weinsberg' in ident or 'ratten' in ident else 'Grimm – Märchen'
    if 'andersen' in creator:return 'Andersen – Märchen'
    if 'hauff' in creator:return 'Hauff – Märchen'
    if ident=='weihnachtsgeschichte' or any(x in creator for x in ('verne','stevenson','defoe','carroll','wells','kipling','irving','burnett','baum','saint-exupéry')):return 'Literarische Klassiker'
    if source.get('kind')=='Film':return 'Filmvorlagen'
    if ident.startswith('comic-quellen-2-'):return 'Weitere überlieferte Stoffe'
    return 'Eigene Quellen'


def category(source):
    manual=source.get('category','').strip()
    if manual:return manual
    ident=source.get('id','');group=collection(source)
    if ident in OVERRIDES:return OVERRIDES[ident]
    if group in ('Mittelalterliche Heldensagen','Nordische Mythen','Antike Mythen'):return 'Heldensagen und Mythen'
    if group in ('Grimm – Märchen','Andersen – Märchen','Hauff – Märchen'):return 'Märchen und Verwandlungen'
    if group=='Literarische Klassiker':return 'Abenteuer und Entdeckungen'
    title=source.get('title','').casefold()
    for result,pattern in RULES:
        if re.search(pattern,title):return result
    if group!='Eigene Quellen':
        # Nur die Erzählung auswerten, nicht die für alle Quellen gleichen Regiehinweise.
        text=source.get('text','')
        text=re.split(r'HANDLUNGSGRUNDLAGE[^\n]*\n',text,maxsplit=1)[-1]
        text=text.split('SCHWERPUNKT DER COMIC-ADAPTION:')[0].casefold()
        patterns=RULES+[( 'Märchen und Verwandlungen',r'verwandel|verwandlung|zwerg|elfen|nixe|wassermann|wassermänn|bergmänn|wünsche erfüll')]
        scores=[(len(re.findall(pattern,text)), -index, label) for index,(label,pattern) in enumerate(patterns)]
        score,_,label=max(scores)
        if score:return label
        return 'Regionale Sagen'
    return 'Eigene Vorlagen'


def decorate(source):
    return {**source,'category':category(source),'collection':collection(source)}
