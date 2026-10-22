import { api } from "../../scripts/api.js";

const clone = value => JSON.parse(JSON.stringify(value));
export function selectedCharacters(node) {
    const value = node.widgets.find(w => w.name === "figuren")?.value;
    try { const cast = JSON.parse(value || "[]"); return Array.isArray(cast) ? cast : []; }
    catch { return []; }
}
export function matchedCharacters(scene, cast) {
    const speakers = (scene.bubbles ?? []).map(b => cast.find(c => [c.id,c.name,...(c.aliases ?? [])].some(n => n.toLocaleLowerCase() === b.speaker.toLocaleLowerCase()))?.id).filter(Boolean);
    if (Array.isArray(scene.characters)) return [...new Set([...scene.characters,...speakers])];
    const words = `${scene.story} ${scene.dialog ?? ""}`.toLocaleLowerCase().match(/[\p{L}\p{N}_]+/gu) ?? [];
    const text = ` ${words.join(" ")} `;
    return cast.filter(c => speakers.includes(c.id) || [c.name, ...(c.aliases ?? [])].some(name => text.includes(` ${name.toLocaleLowerCase().replace(/[^\p{L}\p{N}_]+/gu, " ").trim()} `))).map(c => c.id);
}
export function writeCharacters(node, cast) {
    const widget = node.widgets.find(w => w.name === "figuren");
    if (widget) widget.value = JSON.stringify(cast);
    node.setDirtyCanvas(true, true);
}
async function request(path, options) {
    const response = await api.fetchApi(`/dgx-comics/characters${path}`, options);
    const value = await response.json();
    if (!response.ok) throw Error(value.error ?? `HTTP ${response.status}`);
    return value;
}
export async function refreshLibrary(node) {
    node._characterLibrary = (await request("")).characters;
    if (!node.properties.cast_initialized) {
        const cast=selectedCharacters(node);
        const sysop=node._characterLibrary.find(c=>[c.name,...(c.aliases ?? [])].some(n=>n.toLocaleLowerCase()==="sysop"));
        if(sysop && !cast.some(c=>c.id===sysop.id || [c.name,...(c.aliases ?? [])].some(n=>n.toLocaleLowerCase()==="sysop")) && cast.length<8){
            const selected=clone(sysop);
            if(node.widgets.find(w=>w.name==="comic_art")?.value==="Großstadt-Noir (düster)" && selected.variants?.Noir)selected.story_outfit=selected.variants.Noir;
            writeCharacters(node,[selected,...cast]);
            const saved=node.widgets.find(w=>w.name==="bearbeiteter_plan");
            try{
                const plan=JSON.parse(saved?.value);
                for(const scene of plan.scenes ?? [])scene.characters=[...new Set([...matchedCharacters(scene,cast),sysop.id])];
                saved.value=JSON.stringify(plan);
            }catch{ /* A new story has no saved plan yet. */ }
        }
        node.properties.cast_initialized=true;
    }
}
export function renderLibrary(node, parent, changed) {
    const block = document.createElement("details");
    block.open = node.properties.character_library_open ?? false;
    block.ontoggle = () => { if (node.properties.character_library_open !== block.open) { node.properties.character_library_open = block.open; changed(); } };
    block.style.cssText = "border:1px solid #777;padding:8px;margin-bottom:12px";
    const summary = document.createElement("summary");
    summary.textContent = `Figurenbibliothek · ${selectedCharacters(node).length} für diese Story ausgewählt`;
    summary.style.cursor = "pointer";
    block.append(summary);
    const message = document.createElement("p");
    message.textContent = "Figuren bleiben über mehrere Storys erhalten. Kleidung hier gilt nur für diese Story. Bibliotheksänderungen werden erst mit Übernehmen in die aktuelle Story kopiert.";
    block.append(message);
    const button = (name, callback, target = block) => {
        const b = document.createElement("button"); b.textContent = name;
        b.style.cssText = "padding:6px;margin:4px";
        b.onclick = async () => {
            b.disabled = true;
            try { await callback(); }
            catch (error) { message.textContent = error.message; }
            finally { b.disabled = false; }
        };
        target.append(b); return b;
    };
    const apply = profile => {
        const cast = selectedCharacters(node);
        const index = cast.findIndex(c => c.id === profile.id);
        if (index < 0 && cast.length >= 8) throw Error("Maximal acht Figuren pro Story.");
        const copy = clone(profile);
        copy.story_outfit = index < 0 ? "" : cast[index].story_outfit ?? "";
        if (index < 0) cast.push(copy); else cast[index] = copy;
        writeCharacters(node, cast); changed();
    };
    const referenceInputs=(profile,target,isDraft=false)=>{
        const hint=document.createElement("p");hint.textContent="Referenzbild hochladen: Gesicht, Ganzkörper oder eine andere Ansicht. Zwei Bilder je Figur, maximal 12 MB pro Bild.";
        target.append(hint);
        for(let slot=0;slot<2;slot++){
            const label=document.createElement("label");label.style.display="block";
            label.textContent=slot===0?"Bild 1 (z. B. Gesicht): ":"Bild 2 (optional): ";
            const file=document.createElement("input");file.type="file";file.accept="image/png,image/jpeg,image/webp,image/gif";
            file.setAttribute("aria-label",isDraft?`Referenz ${slot+1} hochladen`:`Bild ${slot+1} hochladen: ${profile.name}`);
            file.onchange=async()=>{
                if(!file.files[0])return;file.disabled=true;
                try{
                    if(file.files[0].size>12*1024*1024)throw Error("Bild maximal 12 MB.");
                    // Save a draft first, retaining edits before attaching its image.
                    let saved=isDraft?await request("",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(profile)}):profile;
                    if(isDraft)node._characterDraft=saved;
                    const data=new FormData();data.append("image",file.files[0]);
                    saved=await request(`/${saved.id}/references/${slot}`,{method:"POST",body:data});
                    if(isDraft)node._characterDraft=clone(saved);
                    else if(node._characterDraft?.id===saved.id)node._characterDraft={...node._characterDraft,references:saved.references,version:saved.version};
                    const cast=selectedCharacters(node);const index=cast.findIndex(c=>c.id===saved.id);
                    if(index>=0){const outfit=cast[index].story_outfit ?? "";cast[index]={...clone(saved),story_outfit:outfit};writeCharacters(node,cast);}
                    await refreshLibrary(node);changed();
                }catch(error){message.textContent=error.message;}
                finally{file.disabled=false;file.value="";}
            };
            label.append(file);target.append(label);
            if(profile.references?.[slot]){
                const img=document.createElement("img");img.src=api.apiURL(`/dgx-comics/characters/${profile.id}/references/${profile.references[slot]}`);
                img.style.cssText="height:80px;max-width:140px;object-fit:contain;margin:5px";
                img.alt=`Bild ${slot+1}: ${profile.name}`;target.append(img);
            }
        }
    };
    button("Bibliothek neu laden", async () => { await refreshLibrary(node); changed(); });
    for (const profile of node._characterLibrary ?? []) {
        const row = document.createElement("div"); row.style.cssText = "display:block;margin:10px 0;padding:8px;border:1px solid #555";
        row.dataset.characterId=profile.id;
        const selectionLabel=document.createElement("label");
        const checkbox = document.createElement("input"); checkbox.type = "checkbox";
        checkbox.checked = selectedCharacters(node).some(c => c.id === profile.id);
        checkbox.onchange = () => {
            try {
                if (checkbox.checked) apply(profile);
                else { writeCharacters(node, selectedCharacters(node).filter(c => c.id !== profile.id)); changed(); }
            } catch(error) { checkbox.checked = false; message.textContent = error.message; }
        };
        selectionLabel.append(checkbox, document.createTextNode(` ${profile.name}`));row.append(selectionLabel);
        button(`Bearbeiten: ${profile.name}`,()=>{node._characterDraft=clone(profile);changed();},row);
        const identity=document.createElement("small");identity.textContent=` · ID ${profile.id.slice(-6)}`;row.append(identity);
        button(`Löschen: ${profile.name}`,()=>{node._characterDeleteId=profile.id;changed();},row);
        if(node._characterDeleteId===profile.id){
            const confirmation=document.createElement("div");confirmation.style.cssText="border:1px solid #d66;padding:8px;margin:8px 0";
            const text=document.createElement("p");text.textContent=`Figur „${profile.name}“ (ID ${profile.id.slice(-6)}) aus der Bibliothek löschen? Bereits gespeicherte Storys und Referenzbilder bleiben erhalten. Eine in dieser Story verwendete Kopie bleibt ebenfalls erhalten.`;confirmation.append(text);
            button("Löschen bestätigen",async()=>{
                await request(`/${profile.id}`,{method:"DELETE",headers:{"Content-Type":"application/json"},body:JSON.stringify({version:profile.version})});
                if(node._characterDraft?.id===profile.id)node._characterDraft=null;
                node._characterDeleteId=null;
                await refreshLibrary(node);changed();
            },confirmation);
            button("Abbrechen",()=>{node._characterDeleteId=null;changed();},confirmation);
            row.append(confirmation);
        }
        referenceInputs(profile,row);
        block.append(row);
    }
    for (const c of selectedCharacters(node)) {
        const card = document.createElement("div"); card.style.cssText = "border:1px solid #555;padding:7px;margin:8px 0";
        card.dataset.storyCharacterId=c.id;
        const name = document.createElement("strong"); name.textContent = `${c.name} · in dieser Story · ID ${c.id.slice(-6)}`;card.append(name);
        const description = document.createElement("p");description.textContent = c.description;card.append(description);
        for (const asset of c.references ?? []) {
            const img = document.createElement("img"); img.src = api.apiURL(`/dgx-comics/characters/${c.id}/references/${asset}`);
            img.alt = `Figurenreferenz ${c.name}`;img.style.cssText = "height:90px;max-width:140px;object-fit:contain;margin:5px";card.append(img);
        }
        for(const encoded of c.inline_references ?? []){
            const image=document.createElement("img");image.src=`data:image/png;base64,${encoded}`;image.alt=`Eingebettete Figurenreferenz ${c.name}`;image.style.cssText="height:90px;max-width:140px;object-fit:contain";card.append(image);
        }
        const outfits = document.createElement("select");
        for (const [label,value] of [["Standardkleidung", ""], ...Object.entries(c.variants ?? {})]) {
            const option = document.createElement("option");option.textContent=label;option.value=value;outfits.append(option);
        }
        outfits.setAttribute("aria-label", `Kleidungsvariante ${c.name}`);
        const label = document.createElement("label");label.textContent = "Kleidung nur für diese Story:";label.style.display="block";
        const input = document.createElement("textarea");input.value=c.story_outfit ?? "";input.placeholder=c.outfit;
        input.maxLength=1000;input.style.cssText="display:block;width:100%;height:55px;background:#151515;color:white";
        input.setAttribute("aria-label", `Story-Kleidung ${c.name}`);
        const saveOutfit = value => { const cast=selectedCharacters(node);cast.find(x=>x.id===c.id).story_outfit=value;writeCharacters(node,cast); };
        input.oninput=()=>saveOutfit(input.value);
        outfits.onchange=()=>{input.value=outfits.value;saveOutfit(input.value);};
        label.append(outfits,input);card.append(label);
        const latest=(node._characterLibrary ?? []).find(x=>x.id===c.id);
        if(latest)button("Aktuelle Bibliotheksversion übernehmen",()=>apply(latest),card);
        else {
            const retained=document.createElement("p");retained.textContent="Aus der Bibliothek gelöscht; die gespeicherte Kopie und Bilder dieser Story bleiben verwendbar.";card.append(retained);
        }
        button("Aus dieser Story entfernen",()=>{writeCharacters(node,selectedCharacters(node).filter(x=>x.id!==c.id));changed();},card);
        block.append(card);
    }
    const editor=document.createElement("details");editor.open=!!node._characterDraft;
    const title=document.createElement("summary");title.textContent="Figur anlegen / bearbeiten";editor.append(title);
    const picker=document.createElement("select");picker.setAttribute("aria-label","Figur bearbeiten");
    const fresh=document.createElement("option");fresh.value="";fresh.textContent="Neue Figur";picker.append(fresh);
    for(const c of node._characterLibrary ?? []){const o=document.createElement("option");o.value=c.id;o.textContent=c.name;picker.append(o);}
    const draft=node._characterDraft ?? {name:"",description:"",aliases:[],outfit:"",variants:{},references:[]};
    picker.value=draft.id ?? "";
    picker.onchange=()=>{node._characterDraft=clone((node._characterLibrary ?? []).find(c=>c.id===picker.value) ?? {name:"",description:"",aliases:[],outfit:"",variants:{},references:[]});changed();};
    editor.append(picker);
    const field=(key,label,height)=>{
        const wrapper=document.createElement("label");wrapper.textContent=label;wrapper.style.display="block";
        const input=document.createElement("textarea");input.setAttribute("aria-label",label);
        input.value=key==="aliases"?(draft.aliases ?? []).join(", "):key==="variants"?Object.entries(draft.variants ?? {}).map(([k,v])=>`${k}: ${v}`).join("\n"):draft[key] ?? "";
        input.style.cssText=`width:100%;height:${height}px;display:block;background:#151515;color:white`;input.maxLength=key==="description"?2500:3000;
        input.oninput=()=>{node._characterDraft=draft;draft[key]=key==="aliases"?input.value.split(",").map(x=>x.trim()).filter(Boolean):key==="variants"?Object.fromEntries(input.value.split("\n").filter(x=>x.includes(":")).map(x=>[x.slice(0,x.indexOf(":")).trim(),x.slice(x.indexOf(":")+1).trim()])):input.value;};
        wrapper.append(input);editor.append(wrapper);
    };
    field("name","Figurenname",32);field("aliases","Alternative Namen, mit Komma getrennt",32);
    field("description","Festes Aussehen: Alter, Gesicht, Haare, Körperbau",85);
    field("outfit","Standardkleidung",55);field("variants","Kleidungsvarianten – pro Zeile Name: Beschreibung",65);
    button("Figur dauerhaft speichern",async()=>{node._characterDraft=await request("",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(draft)});await refreshLibrary(node);changed();},editor);
    if(draft.id){
        button("Für diese Story übernehmen",()=>apply(draft),editor);
    }
    referenceInputs(draft,editor,true);
    block.append(editor);parent.append(block);
}
