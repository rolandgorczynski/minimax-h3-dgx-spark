"""Eigene dramaturgische Ableitungen aus bekannten Comic-Erzählweisen, keine Vorlagenkopien."""
PROFILES={
 'auto':{'label':'Passend zur Geschichte','description':'Konflikt, Entscheidung und Nachwirkung aus der vorhandenen Geschichte entwickeln.','rules':'Wähle einen zur Geschichte passenden emotionalen Schwerpunkt. Eröffne mit einer konkreten Störung statt mit allgemeiner Landschaft. Mache Wunsch und Risiko verständlich. Ein Rückschlag erzwingt eine Entscheidung; die Schlusswirkung folgt aus deren Konsequenz.','sources':[]},
 'one_piece':{'label':'Emotionales Abenteuer · Vorbild One Piece','description':'Persönlicher Wunsch, Bindung, großer Rückschlag und emotionaler Höhepunkt.','rules':'Verankere die Hauptfigur in einem konkreten Wunsch und einer erkennbaren Verletzlichkeit. Zeige, warum der Ausgang persönlich zählt. Kontrastiere leichte Momente und ernste Bedrohung, ohne Tonwechsel beliebig zu setzen. Ein Rückschlag trifft den Wunsch, dann entscheidet sich die Figur zu einem Handeln mit einem Preis. Bereite ein Bildmotiv oder Versprechen vor und löse es emotional ein. Bei wenigen Figuren liegt die Bindung in Erinnerung, Verpflichtung oder Entscheidung; keine zusätzliche Mannschaft erfinden.','sources':['https://www.shueisha.co.jp/history/detail/2022.html','https://avex.jp/onepiece/products/detail.php?artist_cd=OPLCX&id=1016296']},
 'asterix':{'label':'Abenteuer & Humor · Vorbild Asterix','description':'Klares Ziel, verschiedene Figurenstimmen, komische Zuspitzung und Pointe.','rules':'Beginne mit einer verständlichen Routine und einer Störung. Gib Figuren gegensätzliche, nachvollziehbare Haltungen statt austauschbarer Sprüche. Führe ein visuelles oder sprachliches Detail früh ein und steigere dessen Bedeutung durch Variationen. Humor entsteht aus Erwartung und Reaktion und bringt die Handlung weiter. Nach wachsendem Durcheinander folgt eine klare Lösung; ein letzter kleiner Rückbezug setzt die Pointe. Keine willkürlichen Witze in tragische Verluste pressen.','sources':['https://www.hachette.com/actualite/asterix-et-obelix-repartent-en-voyage-le-23-octobre/','https://www.hachette.com/actualite/liris-blanc-le-nouvel-album-dasterix-aux-editions-albert-rene/']},
 'batman':{'label':'Düstere Spannung · Vorbild Batman','description':'Offene Frage, sichtbare Hinweise, moralische Entscheidung und nachhallendes Ende.','rules':'Eröffne mit einer konkreten offenen Frage oder sichtbaren Folge einer Gefahr. Streue einen Hinweis, den der Leser später neu versteht. Lass äußere Bedrohung und innere Unsicherheit aufeinander wirken. Eine plausible erste Deutung reicht nicht; Handlung und Erkenntnis bringen einen neuen Preis ans Licht. Der Höhepunkt verlangt eine Entscheidung mit Folgen. Schließe mit einem starken Echo des Anfangs oder einer begründeten offenen Frage. Dunkelheit, Gewalt und Schweigen müssen jeweils Information oder Bedeutung tragen.','sources':['https://www.dc.com/graphic-novels/detective-comics-2016/batman-detective-comics-vol-1-gotham-nocturne-overture','https://www.dc.com/graphic-novels/batmans-mystery-casebook']}
}


def profile_prompt(key):
    profile=PROFILES[key]
    # Marken- und Figurennamen werden nicht als Bild- oder Plotanweisung an das Modell gegeben.
    return ('ERZÄHLWERKZEUGE: '+profile['description']+'\n'+profile['rules']+
        '\nDies sind abstrakte Erzählmechaniken. Eigene Figuren und Welt beibehalten; keine fremden Figuren, Kostüme, Schauplätze, Sprüche oder konkreten Abenteuer übernehmen. '
        'Der vorhandene Bildstil bleibt verbindlich. Die gewünschte Erzählweise ersetzt ihn nicht.')


def beat_slots(count):
    if count==1:roles=['Verdichteter entscheidender Moment mit sichtbarer Folge']
    elif count==2:roles=['Störung, Wunsch und Hindernis','Entscheidung und ihre Konsequenz']
    elif count==3:roles=['Störung und persönliches Ziel','Druck und Wendung','Entscheidung und Nachwirkung']
    elif count==4:roles=['Starker Einstieg','Ziel trifft auf Widerstand','Wendung erzwingt Entscheidung','Konsequenz und Schlusswirkung']
    elif count==5:roles=['Störung und persönliches Ziel','Widerstand und wachsender Druck','Erster Weg scheitert oder wird fraglich','Entscheidung mit einem Preis','Konsequenz und Schlusswirkung']
    else:roles=['Störung / fesselnder Einstieg','Persönliches Ziel und Einsatz','Widerstand / Druck steigt','Rückschlag / Wendung','Entscheidung mit einem Preis','Konsequenz / emotionaler Abschluss']
    n=len(roles)
    return [{'start':i*count//n+1,'end':(i+1)*count//n,'function':role} for i,role in enumerate(roles)]
