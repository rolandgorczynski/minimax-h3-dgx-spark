"""Beschriftung lesbar einpassen; ungelöste Texte als editierbaren Entwurf erhalten."""
import copy
from PIL import Image,ImageDraw
from lettering import DESIGN,issues,intersects,contains


def fit_scene(scene,number=1,names=None):
    scene=copy.deepcopy(scene);size=scene.get('canvas_size',[768,672]);names=names or {};warnings=[];changes=[]
    before=scene.get('dialog','');scene['dialog']=DESIGN.clean_text(before)
    if before!=scene['dialog']:changes.append({'field':'dialog','kind':'whitespace'})
    originals=scene.get('bubbles',[]);bubbles=DESIGN.validate_bubbles(originals)
    for i,(old,new) in enumerate(zip(originals,bubbles)):
        if old['text']!=new['text']:changes.append({'field':'bubbles','bubble':i,'kind':'whitespace'})
    canvas=Image.new('RGB',tuple(size),'white');draw=ImageDraw.Draw(canvas)
    placed=[];protected=scene.get('protected_areas',[])
    floor=DESIGN.caption_band(scene['dialog'],size)/size[1]+.015 if scene['dialog'] else .10
    for i,bubble in enumerate(bubbles):
        def valid(candidate):
            layout={'dialog':scene['dialog'],'bubbles':placed+[candidate],'protected_areas':protected}
            if issues(layout,size):return False
            if any(intersects(candidate,other) or contains(candidate,other['tip_x'],other['tip_y']) for other in bubbles[i+1:]):return False
            try:DESIGN._speech(draw,candidate,names,tuple(size))
            except ValueError:return False
            return True
        selected=bubble
        if not valid(bubble):
            choices=[]
            widths=sorted(set([bubble['w'],.38,.42,.46,.50,.55,.60,.70,.85]))
            heights=sorted(set([bubble['h'],.16,.20,.24,.28,.32,.40,.50,.60]))
            for w in widths:
                if w+1e-8<bubble['w']:continue
                for h in heights:
                    if h+1e-8<bubble['h']:continue
                    for x in dict.fromkeys([bubble['x'],max(.01,min(bubble['x']+bubble['w']/2-w/2,.99-w)),max(.01,.99-w)]):
                        for y in dict.fromkeys([max(floor,bubble['y']),floor,.49,.68]):
                            if x+w>.995 or y+h>.995:continue
                            candidate={**bubble,'x':x,'y':y,'w':w,'h':h}
                            score=(w*h-bubble['w']*bubble['h'])+abs(x-bubble['x'])+abs(y-bubble['y'])
                            choices.append((score,candidate))
            chosen=next((candidate for _,candidate in sorted(choices,key=lambda item:item[0]) if valid(candidate)),None)
            if chosen:
                selected=chosen;changes.append({'field':'bubbles','bubble':i,'kind':'geometry','before':{k:bubble[k] for k in ('x','y','w','h')},'after':{k:selected[k] for k in ('x','y','w','h')}})
            else:warnings.append({'panel':number,'field':'bubbles','bubble':i,'message':f'Sprechblase {i+1}: Text oder Position braucht eine manuelle Anpassung. Der vollständige Text bleibt im Blaseneditor.'})
        placed.append(selected)
    scene['bubbles']=placed
    try:DESIGN.panel(canvas,scene['dialog'],number,[],names,canvas_size=scene.get('canvas_size'))
    except ValueError:warnings.append({'panel':number,'field':'dialog','message':'Erzählertext braucht eine manuelle Anpassung. Der vollständige Text bleibt im Blaseneditor.'})
    if warnings:scene['lettering_draft']=True
    else:scene.pop('lettering_draft',None)
    return scene,changes,warnings


def prepare(scenes,cast):
    names={c['id']:c['name'] for c in cast};result=[];changes=[];warnings=[]
    for i,scene in enumerate(scenes):
        fixed,local,problems=fit_scene(scene,i+1,names);result.append(fixed);changes.extend({'panel':i+1,**change} for change in local);warnings.extend(problems)
    return result,{'adjustments':changes,'warnings':warnings,'unresolved_panels':sorted({w['panel'] for w in warnings})}


def accept_preflight(scenes,fit,report):
    """Nur bekannte Platzprobleme als Entwurf zulassen, keine Struktur- oder Sprecherfehler."""
    for issue in fit['issues']:
        if 'Der Text ist zu lang für die Sprechblase' not in issue['message']:raise ValueError('Beschriftung ungültig: '+issue['message'])
        panel=issue['panel'];scenes[panel-1]['lettering_draft']=True
        if panel not in report['unresolved_panels']:
            report['unresolved_panels'].append(panel);report['warnings'].append({'panel':panel,'message':'Text passt noch nicht. Bitte nach dem Zeichnen im Blaseneditor anpassen.'})
    return report


def record(store,job,report):
    pending=bool(report['unresolved_panels']);notes=[f'Kachel {w["panel"]}: {w["message"]}' for w in report['warnings']]
    if pending:notes.insert(0,'ENTWURF: Beschriftung unter „Sprechblasen positionieren“ korrigieren. Vollständige Texte sind gespeichert.')
    store.write(job,'lettering-report.json',report);store.update(job,lettering_unresolved=pending,lettering_warnings=notes)
    return notes
