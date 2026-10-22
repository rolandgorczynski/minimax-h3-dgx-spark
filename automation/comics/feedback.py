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
        raise ValueError('bewertungen und optional kommentar senden.')
    ratings=value.get('bewertungen')
    if not isinstance(ratings,dict) or set(ratings)!=set(CRITERIA):
        raise ValueError('Alle fünf Kriterien mit 1–5 bewerten: '+', '.join(CRITERIA))
    if any(type(score) is not int or not 1<=score<=5 for score in ratings.values()):
        raise ValueError('Bewertungen müssen ganze Zahlen von 1 bis 5 sein.')
    comment=value.get('kommentar','')
    if not isinstance(comment,str) or len(comment)>2000:raise ValueError('Kommentar maximal 2000 Zeichen.')
    return {'bewertungen':ratings,'kommentar':comment.strip()}
