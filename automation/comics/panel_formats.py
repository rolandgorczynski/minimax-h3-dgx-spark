"""Seitenvorlagen bestimmen Bildformat, Beschriftung und native Sampling-Auflösung."""
import copy,math
from lettering import LAYOUT,DESIGN


def sizes(template):
    template=LAYOUT.validate_template(template);info=LAYOUT.TEMPLATES[template];aspect=LAYOUT.template_aspect(template)
    result=[]
    smallest=min(w*h for x,y,w,h in info['slots'])
    for x,y,w,h in info['slots']:
        ratio=w/h*aspect;width=max(768,math.ceil(384*ratio/16)*16);height=math.ceil(width/ratio/16)*16
        emphasis=math.sqrt(w*h/smallest);width=math.ceil(width*emphasis/16)*16;height=math.ceil(height*emphasis/16)*16
        factor=min(1,2304/width,3072/height);width=max(384,math.floor(width*factor/16)*16);height=max(320,math.floor(height*factor/16)*16)
        result.append(list(DESIGN.validate_canvas_size((width,height))))
    return result


def apply(scenes,template):
    result=copy.deepcopy(scenes);targets=sizes(template) if template!='standard' else [[768,672]]
    for i,scene in enumerate(result):
        target=targets[i%len(targets)];old=scene.get('canvas_size',[768,672])
        if template!='standard':scene['bubbles']=DESIGN.validate_bubbles(scene.get('bubbles',[]))
        if target!=old:
            previous=DESIGN.caption_band(scene.get('dialog',''),old)/old[1];new=DESIGN.caption_band(scene.get('dialog',''),target)/target[1]
            for bubble in scene.get('bubbles',[]):
                for key in ('y','tip_y'):
                    if key in bubble:bubble[key]=max(.005,min(.995,new+(bubble[key]-previous)*(1-new)/(1-previous)))
                if 'h' in bubble:bubble['h']*= (1-new)/(1-previous)
            for area in scene.get('protected_areas',[]):
                area['y']=max(0,new+(area['y']-previous)*(1-new)/(1-previous));area['h']=min(area['h']*(1-new)/(1-previous),1-area['y'])
        if template=='standard':scene.pop('canvas_size',None);scene.pop('render_size',None)
        else:scene['canvas_size']=target;scene['render_size']=DESIGN.art_render_size(target,scene.get('dialog',''))
    return result
