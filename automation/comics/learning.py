"""Evidence-linked self reflection, not an assertion that quality always improves."""
import copy

AREAS=('story','scenes','lettering','visual')


def record(reports,area,iteration,review,target=0):
    reports.setdefault('history',[]).append({'area':area,'round':iteration,'target':target,**copy.deepcopy(review)})


def evidence(reports):
    history=reports.get('history')
    if history is None:
        history=[]
        for area in AREAS:
            values=reports.get(area,[])
            for target,value in enumerate(values if isinstance(values,list) else [values]):
                if isinstance(value,dict):history.append({'area':area,'round':0,'target':target,**value})
    findings=[];groups={}
    for index,item in enumerate(history):
        approved=item.get('approved',item.get('valid',False))
        issues=[issue if isinstance(issue,str) else issue.get('message','') for issue in item.get('issues',[])]
        groups.setdefault((item['area'],item.get('target',0)),[]).append({'approved':approved,'issues':len(issues)})
        for number,issue in enumerate(issues[:5]):
            findings.append({'id':f'{item["area"]}:{index}:{number}','area':item['area'],'issue':issue[:500],
                             'group':[item['area'],item.get('target',0)]})
    comparisons=[]
    for (area,target),values in groups.items():
        first,last=values[0],values[-1]
        outcome='not_compared' if len(values)<2 else 'resolved' if not first['approved'] and last['approved'] else 'regressed' if first['approved'] and not last['approved'] or last['issues']>first['issues'] else 'fewer_findings' if last['issues']<first['issues'] else 'unchanged'
        comparisons.append({'area':area,'target':target,'before':first,'after':last,'outcome':outcome})
    return {'findings':findings[:50],'comparisons':comparisons,'measurement':'model_reviews_not_objective_quality'}


def validate_lessons(value,facts):
    if not isinstance(value,dict) or not isinstance(value.get('lessons'),list) or len(value['lessons'])>3:raise ValueError('Maximal drei Lernerfahrungen erwartet.')
    known={item['id']:item for item in facts['findings']};lessons=[]
    for item in value['lessons']:
        if not isinstance(item,dict) or not isinstance(item.get('rule'),str) or not 10<=len(item['rule'])<=300 or item.get('evidence_ref') not in known:
            raise ValueError('Jede Lernregel braucht eine kurze Handlungsempfehlung und eine vorhandene Beleg-ID.')
        finding=known[item['evidence_ref']]
        resolved=any([c['area'],c['target']]==finding['group'] and c['outcome']=='resolved' for c in facts['comparisons'])
        lessons.append({'area':finding['area'],'rule':item['rule'],'evidence_ref':finding['id'],
                        'status':'supported_by_model_comparison' if resolved else 'hypothesis'})
    if facts['findings'] and not lessons:raise ValueError('Mindestens eine konkrete Lernerfahrung zu den Befunden erwartet.')
    return {'lessons':lessons}
