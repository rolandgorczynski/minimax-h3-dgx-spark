"""Optional editorial feedback, independent from generation triggers."""
CRITERIA={
    'verstaendlichkeit':'War die Geschichte verständlich und logisch?',
    'spannung':'War die Geschichte interessant oder spannend?',
    'figuren':'Waren die Figuren überzeugend und wiedererkennbar?',
    'dialoge':'Waren Sprache und Dialoge passend?',
    'ende':'Hat das Ende oder die Pointe funktioniert?',
}


def validate_feedback(value):
    if not isinstance(value,dict) or set(value)-{'bewertungen','kommentar'}:
        raise ValueError('Kommentar und optional Punktbewertungen senden.')
    ratings=value.get('bewertungen',{})
    if not isinstance(ratings,dict) or set(ratings)-set(CRITERIA):
        raise ValueError('Unbekannte Punktbewertung.')
    if any(type(score) is not int or not 1<=score<=5 for score in ratings.values()):
        raise ValueError('Bewertungen müssen ganze Zahlen von 1 bis 5 sein.')
    comment=value.get('kommentar','')
    if not isinstance(comment,str) or len(comment)>2000:raise ValueError('Kommentar maximal 2000 Zeichen.')
    if not ratings and not comment.strip():raise ValueError('Bitte einen Kommentar oder mindestens eine Punktbewertung eingeben.')
    return {'bewertungen':ratings,'kommentar':comment.strip()}
