import { api } from "../../scripts/api.js";
import { matchedCharacters } from "./characters.js";
const NS="http://www.w3.org/2000/svg";
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
export function newBubble(index,speaker="Sysop",text="") {
    return {speaker,text,expression:"normal",x:.08+(index%2)*.46,y:.23+Math.floor(index/2)*.24,w:.38,h:.18,
        tip_x:.25+(index%2)*.5,tip_y:Math.min(.96,.48+Math.floor(index/2)*.22),show_name:true};
}
export function renderSpeechEditor(node,section,scene,index,cast,preview,save,rerender) {
    const number=index+1;
    if(Array.isArray(scene.bubbles)) scene.bubbles=scene.bubbles.map((b,i)=>({...newBubble(i,b.speaker,b.text),...b}));
    const container=document.createElement("div");
    const info=document.createElement("p");info.textContent="Sprechblasen: Sprecher auswählen. In der Vorschau den gelben Rahmen verschieben, unten rechts die Größe ändern und den roten Punkt zum Sprecher ziehen. Änderungen werden ohne Bildmodell angezeigt.";
    container.append(info);
    const frame=document.createElement("div");
    frame.style.cssText="position:relative;width:100%;max-width:768px;aspect-ratio:768/672;margin:8px auto;background:#75808b;touch-action:none";
    const image=document.createElement("img");image.alt=`Beschriftungsvorschau Kachel ${number}`;
    image.style.cssText="display:block;width:100%;height:100%;pointer-events:none";
    if(preview)image.src=api.apiURL(`/view?${new URLSearchParams(preview)}`);
    frame.append(image);
    const svg=document.createElementNS(NS,"svg");svg.setAttribute("viewBox","0 0 768 672");
    svg.style.cssText="position:absolute;inset:0;width:100%;height:100%;touch-action:none";frame.append(svg);container.append(frame);
    const status=document.createElement("p");status.setAttribute("role","status");container.append(status);
    let timer,controller,url,disposed=false,sequence=0,drag=null;
    const controls=[];
    const refresh=()=>{
        clearTimeout(timer);const version=++sequence;
        timer=setTimeout(async()=>{
            controller?.abort();controller=new AbortController();
            try {
                const art=preview?{...preview,filename:preview.filename.replace(/_panel\.png$/,"_art.png")}:null;
                const response=await api.fetchApi("/dgx-comics/lettering-preview",{method:"POST",headers:{"Content-Type":"application/json"},
                    body:JSON.stringify({scene,number,art,names:Object.fromEntries(cast.map(c=>[c.id,c.name]))}),signal:controller.signal});
                if(!response.ok){const error=await response.json();throw Error(error.error ?? "Vorschau fehlgeschlagen");}
                const blob=await response.blob();
                if(disposed || version!==sequence)return;
                const next=URL.createObjectURL(blob);image.src=next;if(url)URL.revokeObjectURL(url);url=next;
                status.textContent=preview?"Vorschau aktualisiert. Weiter speichert den Comic mit dieser Beschriftung.":"Positionierungsvorschau ohne Illustration. Nach der Bilderzeugung die Spitzen an den Figuren ausrichten.";
            }catch(error){if(error.name!=="AbortError" && !disposed)status.textContent=error.message;}
        },120);
    };
    const changed=()=>{save();drawHandles();refresh();};
    const update=(bubble,key,value)=>{
        if(key==="x")bubble.x=clamp(value,.005,.995-bubble.w);
        else if(key==="y")bubble.y=clamp(value,.005,.995-bubble.h);
        else if(key==="w")bubble.w=clamp(value,.15,.995-bubble.x);
        else if(key==="h")bubble.h=clamp(value,.08,.995-bubble.y);
        else bubble[key]=clamp(value,.005,.995);
    };
    const start=(event,bubble,kind)=>{
        if(event.button!==0)return;
        event.preventDefault();event.stopPropagation();
        const bounds=svg.getBoundingClientRect();
        drag={bubble,kind,startX:event.clientX,startY:event.clientY,bounds,old:{...bubble}};
        svg.setPointerCapture(event.pointerId);
    };
    function drawHandles(){
        svg.replaceChildren();
        for(const [i,b] of (scene.bubbles ?? []).entries()){
            const element=(type,attrs,label,kind)=>{
                const el=document.createElementNS(NS,type);
                for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));
                el.setAttribute("aria-label",`Kachel ${number}: Blase ${i+1} ${label}`);
                el.setAttribute("role","button");el.setAttribute("tabindex","0");el.style.cursor=kind==="resize"?"nwse-resize":"move";
                el.onpointerdown=e=>start(e,b,kind);
                el.onkeydown=e=>{
                    const d={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key];
                    if(!d)return;e.preventDefault();e.stopPropagation();const step=e.shiftKey?.001:.01;
                    const keys=kind==="tip"?["tip_x","tip_y"]:kind==="resize"?["w","h"]:["x","y"];
                    update(b,keys[0],b[keys[0]]+d[0]*step);update(b,keys[1],b[keys[1]]+d[1]*step);changed();
                    [...svg.children].find(x=>x.getAttribute("aria-label")===el.getAttribute("aria-label"))?.focus();
                };
                svg.append(el);
            };
            element("rect",{x:b.x*768,y:b.y*672,width:b.w*768,height:b.h*672,fill:"transparent",stroke:"#ffca28","stroke-width":2,"stroke-dasharray":"8 5"},"verschieben","body");
            element("rect",{x:(b.x+b.w)*768-9,y:(b.y+b.h)*672-9,width:18,height:18,fill:"#ffca28",stroke:"black"},"Größe ändern","resize");
            element("circle",{cx:b.tip_x*768,cy:b.tip_y*672,r:10,fill:"#ef5350",stroke:"white","stroke-width":2},"Spitze verschieben","tip");
            const inputs=controls[i];if(inputs)for(const [key,input] of Object.entries(inputs))input.value=Math.round(b[key]*1000)/10;
        }
    }
    svg.onpointermove=event=>{
        if(!drag)return;event.preventDefault();event.stopPropagation();
        const dx=(event.clientX-drag.startX)/drag.bounds.width,dy=(event.clientY-drag.startY)/drag.bounds.height;
        const keys=drag.kind==="tip"?["tip_x","tip_y"]:drag.kind==="resize"?["w","h"]:["x","y"];
        update(drag.bubble,keys[0],drag.old[keys[0]]+dx);update(drag.bubble,keys[1],drag.old[keys[1]]+dy);changed();
    };
    const end=event=>{if(!drag)return;event.preventDefault();event.stopPropagation();drag=null;if(svg.hasPointerCapture(event.pointerId))svg.releasePointerCapture(event.pointerId);refresh();};
    svg.onpointerup=end;svg.onpointercancel=end;
    const button=(label,callback,target=container)=>{const b=document.createElement("button");b.textContent=label;b.style.cssText="padding:7px;margin:4px";b.onclick=callback;target.append(b);return b;};
    for(const [i,bubble] of (scene.bubbles ?? []).entries()){
        const card=document.createElement("section");card.style.cssText="border:1px solid #666;padding:8px;margin:8px 0";
        const heading=document.createElement("strong");heading.textContent=`Sprechblase ${i+1}`;card.append(heading);
        const picker=document.createElement("select");picker.setAttribute("aria-label",`Kachel ${number}: Blase ${i+1} Sprecher`);
        const options=[...[...cast].map(c=>[c.id,c.name]),["__custom","Andere Figur …"]];
        for(const [value,label] of options){const option=document.createElement("option");option.value=value;option.textContent=label;picker.append(option);}
        const known=options.some(([value])=>value===bubble.speaker);picker.value=known?bubble.speaker:"__custom";
        const speaker=document.createElement("input");speaker.value=known?"":bubble.speaker;speaker.placeholder="Name des Sprechers";speaker.maxLength=100;
        speaker.setAttribute("aria-label",`Kachel ${number}: Blase ${i+1} Sprechername`);speaker.hidden=picker.value!=="__custom";
        picker.onchange=()=>{
            speaker.hidden=picker.value!=="__custom";
            bubble.speaker=picker.value==="__custom"?(speaker.value || "Figur"):picker.value;
            if(cast.some(c=>c.id===bubble.speaker)){
                scene.characters=[...new Set([...matchedCharacters(scene,cast),bubble.speaker])];
            }
            for(const character of cast){
                const assignment=[...section.querySelectorAll('input[type="checkbox"]')].find(el=>el.getAttribute("aria-label")===`Kachel ${number}: Figur ${character.name}`);
                if(assignment){
                    assignment.checked=matchedCharacters(scene,cast).includes(character.id);
                    assignment.disabled=scene.bubbles.some(b=>b.speaker===character.id);
                    assignment.title=assignment.disabled?"Diese Figur spricht in dieser Kachel.":"";
                }
            }
            changed();
        };
        speaker.oninput=()=>{bubble.speaker=speaker.value;changed();};
        card.append(document.createTextNode(" Sprecher: "),picker,speaker);
        const text=document.createElement("textarea");text.value=bubble.text;text.maxLength=400;
        text.setAttribute("aria-label",`Kachel ${number}: Blase ${i+1} Text`);text.style.cssText="display:block;width:100%;height:65px;box-sizing:border-box;background:#151515;color:white";
        text.oninput=()=>{bubble.text=text.value;changed();};card.append(text);
        const expression=document.createElement("select");expression.setAttribute("aria-label",`Kachel ${number}: Blase ${i+1} Ausdruck`);
        for(const [value,label] of [["normal","Sprechen"],["shout","Schreien"],["whisper","Flüstern"]]){const o=document.createElement("option");o.value=value;o.textContent=label;expression.append(o);}
        expression.value=bubble.expression;expression.onchange=()=>{bubble.expression=expression.value;changed();};card.append(expression);
        const nameLabel=document.createElement("label");const show=document.createElement("input");show.type="checkbox";show.checked=bubble.show_name;
        show.onchange=()=>{bubble.show_name=show.checked;changed();};nameLabel.append(show,document.createTextNode("Sprechernamen anzeigen"));card.append(nameLabel);
        const position=document.createElement("details");const title=document.createElement("summary");title.textContent="Position und Größe in Prozent";position.append(title);
        controls[i]={};
        for(const [key,label] of [["x","Links"],["y","Oben"],["w","Breite"],["h","Höhe"],["tip_x","Spitze links"],["tip_y","Spitze oben"]]){
            const wrapper=document.createElement("label");wrapper.textContent=label+" ";const input=document.createElement("input");input.type="number";input.min=0;input.max=100;input.step=.5;input.value=Math.round(bubble[key]*1000)/10;input.style.width="65px";
            input.setAttribute("aria-label",`Kachel ${number}: Blase ${i+1} ${label}`);
            input.onchange=()=>{update(bubble,key,Number(input.value)/100);changed();};controls[i][key]=input;wrapper.append(input);position.append(wrapper);
        }
        card.append(position);
        button(`Sprechblase ${i+1} entfernen`,()=>{scene.bubbles.splice(i,1);save();rerender();},card);container.append(card);
    }
    const add=button("Sprechblase hinzufügen",()=>{
        scene.bubbles ??=[];scene.bubbles.push(newBubble(scene.bubbles.length,cast[0]?.id ?? "Figur"));save();rerender();
    });add.disabled=(scene.bubbles?.length ?? 0)>=6;
    button("Benannte Dialoge aus Szene übernehmen",()=>{
        const pattern=/([A-ZÄÖÜ][\wÄÖÜäöüß -]{0,59}):\s*["„“»]([^"“”«»\n]{1,400})["“”«»]/g;
        const matches=[...`${scene.story}\n${scene.dialog ?? ""}`.matchAll(pattern)];
        if(!matches.length){status.textContent='Keine benannten Dialoge gefunden. Beispiel: Markus: "Nein! Nein!"';return;}
        if(matches.length>6){status.textContent="Mehr als sechs Dialoge gefunden. Bitte auf mehrere Kacheln aufteilen.";return;}
        scene.bubbles ??=[];
        for(const [,name,text] of matches){
            const canonical=cast.find(c=>[c.name,...(c.aliases ?? [])].some(n=>n.toLocaleLowerCase()===name.trim().toLocaleLowerCase()))?.id ?? name.trim();
            if(scene.bubbles.some(b=>b.speaker===canonical && b.text===text.trim()))continue;
            if(scene.bubbles.length>=6)break;
            const b=newBubble(scene.bubbles.length,canonical,text.trim());if(text.split("!").length>2)b.expression="shout";scene.bubbles.push(b);
        }
        save();rerender();
    });
    section.append(container);drawHandles();refresh();
    return {refresh,dispose:()=>{disposed=true;clearTimeout(timer);controller?.abort();if(url)URL.revokeObjectURL(url);}};
}
