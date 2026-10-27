/* Figuren für einzelne Geschichten und die wiederverwendbare Bibliothek. */
let characterLibrary=[],characterLibraryLoaded=false,characterLibraryLoading=false,characterImageUrls=[],characterRenderTicket=0,characterPreviewObserver=null;
const characterAlignments={'':'Nicht festgelegt',lawful_good:'Rechtschaffen gut',neutral_good:'Neutral gut',chaotic_good:'Chaotisch gut',lawful_neutral:'Rechtschaffen neutral',true_neutral:'Neutral',chaotic_neutral:'Chaotisch neutral',lawful_evil:'Rechtschaffen böse',neutral_evil:'Neutral böse',chaotic_evil:'Chaotisch böse'};
const characterFields=[['name','Name',100,'input'],['description','Festes Aussehen',2500,'textarea'],['outfit','Kleidung',1000,'textarea'],['backstory','Vorgeschichte',2500,'textarea'],['personality','Persönlichkeit',1200,'textarea'],['motivation','Motivation / Ziele',1200,'textarea']];
function markCharacterDirty(){dirty=true;$('definition-state').textContent='Ungespeicherte Änderungen an Figuren';}
async function loadCharacterLibrary(){if(characterLibraryLoading)return;characterLibraryLoading=true;$('character-library-status').textContent='Figurenbibliothek wird geladen …';try{const value=await(await api('/characters')).json();characterLibrary=value.characters;characterLibraryLoaded=true;$('character-library-status').textContent=characterLibrary.length+' wiederverwendbare Figuren';drawCharacterEditor({preserveOpen:true})}catch(e){$('character-library-status').textContent=e.message}finally{characterLibraryLoading=false}}
async function characterLibrarySnapshot(character){
 const snapshot=structuredClone(character);
 if(snapshot.references?.length&&!snapshot.inline_references?.length){
  snapshot.inline_references=[];
  for(const asset of snapshot.references)snapshot.inline_references.push(await blobBase64(await file('/characters/'+character.id+'/references/'+asset)));
 }
 snapshot.references=[];
 return snapshot;
}
function replaceStoryCharacter(payload,targetId,libraryCharacter){
 const target=payload.characters?.find(c=>c.id===targetId);
 if(!target)throw Error('Die zu ersetzende Figur ist nicht mehr in dieser Geschichte.');
 if(!libraryCharacter?.id||!libraryCharacter.name?.trim())throw Error('Eine gültige Bibliotheksfigur auswählen.');
 const others=payload.characters.filter(c=>c.id!==targetId),fold=value=>value.trim().toLocaleLowerCase('de');
 if(others.some(c=>c.id===libraryCharacter.id||c.library_source_id===libraryCharacter.id))throw Error('Diese Bibliotheksfigur wird bereits für eine andere Figur dieser Geschichte verwendet.');
 const taken=new Set(others.flatMap(c=>[c.name,...(c.aliases||[])]).map(fold));
 const snapshot=structuredClone(libraryCharacter);snapshot.id=targetId;snapshot.library_source_id=libraryCharacter.id;
 snapshot.name=target.name;delete snapshot.story_outfit;
 const used=new Set([fold(snapshot.name)]),aliases=[];
 for(const value of [...(target.aliases||[])]){
  if(!value?.trim()||used.has(fold(value)))continue;
  aliases.push(value.trim());used.add(fold(value));
 }
 if([snapshot.name,...aliases].some(name=>taken.has(fold(name))))throw Error('Ein Name oder Alias dieser Bibliotheksfigur gehört bereits zu einer anderen Figur der Geschichte.');
 if(aliases.length>12)throw Error('Der Tausch würde mehr als zwölf alternative Namen erzeugen. Figuren-Namen und Aliasse zuerst bereinigen.');
 snapshot.aliases=aliases;
 const result=structuredClone(payload),oldNames=new Set([target.name,...(target.aliases||[])].map(fold));
 result.character_replacement_originals??={};
 if(!result.character_replacement_originals[targetId])result.character_replacement_originals[targetId]={
  profile:structuredClone(target),
  reference_overrides:structuredClone(payload.reference_overrides?.[targetId]??null),
  outfit:structuredClone(payload.outfits?.[targetId]??null),
  library_linked:(payload.library_ids||[]).includes(targetId)
 };
 result.characters=result.characters.map(c=>c.id===targetId?snapshot:c);
 result.library_ids=(result.library_ids||[]).filter(id=>id!==targetId&&id!==libraryCharacter.id);
 for(const key of ['reference_overrides','outfits'])if(result[key])delete result[key][targetId];
 for(const scene of result.scenes||[]){
  scene.characters=[...new Set((scene.characters||[]).map(id=>oldNames.has(fold(id))?targetId:id))];
  for(const bubble of scene.bubbles||[])if(oldNames.has(fold(bubble.speaker||'')))bubble.speaker=targetId;
 }
 if(oldNames.has(fold(result.narrator_character_id||'')))result.narrator_character_id=targetId;
 return result;
}
function restoreStoryCharacter(payload,targetId){
 const original=payload.character_replacement_originals?.[targetId];
 if(!original||!payload.characters?.some(c=>c.id===targetId))throw Error('Für diese Figur ist kein ursprüngliches Profil gespeichert.');
 const fold=value=>value.trim().toLocaleLowerCase('de');
 const names=new Set([original.profile.name,...(original.profile.aliases||[])].map(fold));
 if(payload.characters.some(c=>c.id!==targetId&&[c.name,...(c.aliases||[])].some(n=>names.has(fold(n)))))throw Error('Ein ursprünglicher Name gehört inzwischen zu einer anderen Figur. Bitte zuerst den Namenskonflikt beheben.');
 const result=structuredClone(payload);
 result.characters=result.characters.map(c=>c.id===targetId?structuredClone(original.profile):c);
 for(const [key,value]of [['reference_overrides',original.reference_overrides],['outfits',original.outfit]]){
  if(value!==null){result[key]??={};result[key][targetId]=structuredClone(value)}
  else if(result[key])delete result[key][targetId];
 }
 result.library_ids=(result.library_ids||[]).filter(id=>id!==targetId);
 if(original.library_linked)result.library_ids.push(targetId);
 delete result.character_replacement_originals[targetId];
 return result;
}
function characterLibraryChoice(item,ticket,choose){
 const tile=document.createElement('button');tile.type='button';tile.className='character-library-choice';tile.dataset.libraryChoice=item.id;tile.setAttribute('aria-label','Figur auswählen: '+item.name);tile.setAttribute('aria-pressed','false');
 const image=document.createElement('img'),placeholder=document.createElement('span'),name=document.createElement('strong');image.alt='Referenzbild von '+item.name;image.hidden=true;placeholder.className='character-library-choice-placeholder';name.textContent=item.name;
 const picture=characterPicture(item,'library');placeholder.textContent=picture?'Vorschau wird geladen …':'Kein Referenzbild';
 image.onerror=()=>{image.hidden=true;placeholder.hidden=false;placeholder.textContent='Bild nicht verfügbar'};
 const show=src=>{if(ticket!==characterRenderTicket)return;image.src=src;image.hidden=false;placeholder.hidden=true};
 const load=async()=>{if(ticket!==characterRenderTicket)return;try{if(picture?.inline)show('data:image/png;base64,'+picture.inline);else if(picture?.path){const blob=await file(picture.path);if(ticket!==characterRenderTicket)return;const url=URL.createObjectURL(blob);characterImageUrls.push(url);show(url)}}catch(error){if(ticket===characterRenderTicket){image.hidden=true;placeholder.hidden=false;placeholder.textContent='Bild nicht verfügbar'}}};
 if(picture){
  if(typeof IntersectionObserver==='function'){
   characterPreviewObserver??=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting){characterPreviewObserver.unobserve(entry.target);entry.target.loadCharacterPreview?.()}},{rootMargin:'100px'});
   tile.loadCharacterPreview=load;characterPreviewObserver.observe(tile);
  }else load();
 }
 tile.onclick=()=>choose(item.id);tile.append(image,placeholder,name);return tile;
}
function characterReplacementPicker(character,ticket){
 const group=document.createElement('fieldset'),legend=document.createElement('legend');group.className='character-replacement-picker';legend.textContent='Durch Bibliotheksfigur ersetzen';group.append(legend);
 const original=editorPayload.character_replacement_originals?.[character.id];
 const originalChoice=original?{...structuredClone(original.profile),id:'__original__',reference_character_id:original.profile.id,name:'Ursprüngliche Figur · '+original.profile.name}:null;
 if(originalChoice&&original.reference_overrides?.length)originalChoice.inline_references=structuredClone(original.reference_overrides);
 const choices=originalChoice?[originalChoice,...characterLibrary]:characterLibrary;

 if(!characterLibraryLoaded){
  const load=document.createElement('button');load.type='button';load.textContent=characterLibraryLoading?'Bibliothek wird geladen …':'Bibliothek laden';load.disabled=characterLibraryLoading;load.onclick=()=>loadCharacterLibrary();group.append(load);if(!originalChoice)return group;
 }
 const label=document.createElement('label'),select=document.createElement('select');select.dataset.characterReplacement=character.id;label.append(document.createTextNode('Gespeicherte Figur'),select);
 const blank=document.createElement('option');blank.value='';blank.textContent='Bibliotheksfigur auswählen …';select.append(blank);
 for(const item of choices){const option=document.createElement('option');option.value=item.id;option.textContent=item.name;select.append(option)}
 const gallery=document.createElement('div');gallery.className='character-library-picker-grid';gallery.dataset.characterReplacementGallery=character.id;gallery.setAttribute('role','group');gallery.setAttribute('aria-label','Bibliotheksfiguren mit Bild auswählen');
 gallery.replaceChildren(...choices.map(item=>characterLibraryChoice(item,ticket,id=>{select.value=id;select.dispatchEvent(new Event('change',{bubbles:true}))})));
 const image=document.createElement('img');image.className='character-photo character-replacement-preview';image.hidden=true;image.alt='Vorschau der Bibliotheksfigur';image.dataset.characterReplacementPreview=character.id;image.tabIndex=0;image.setAttribute('role','button');image.title='Vorschaubild vergrößern';image.setAttribute('aria-label','Vorschaubild vergrößern');
 image.onclick=()=>openCharacterPicture(image,choices.find(c=>c.id===select.value)?.name);
 image.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();image.click()}};
 const note=document.createElement('p');note.textContent=characterLibrary.length?'Aussehen, Eigenschaften und Referenzbilder übernehmen. Der Name in der Geschichte bleibt erhalten. Szenen und Gespräche bleiben erhalten. Kachelbeschreibungen und besondere Kleidungsanweisungen anschließend prüfen.':'Noch keine gespeicherten Figuren in der Bibliothek.';
 const apply=document.createElement('button');apply.type='button';apply.textContent='Durch diese Figur ersetzen';apply.dataset.characterReplacementApply=character.id;apply.disabled=true;
 const status=document.createElement('p');status.setAttribute('role','status');status.dataset.characterReplacementStatus=character.id;
 let previewTicket=0;
 select.onchange=()=>{
  const current=++previewTicket,chosen=choices.find(c=>c.id===select.value);apply.disabled=!chosen;apply.textContent=chosen?.id==='__original__'?'Ursprüngliche Figur wiederherstellen':'Durch diese Figur ersetzen';image.hidden=true;status.textContent='';
  for(const tile of gallery.children)tile.setAttribute('aria-pressed',String(tile.dataset.libraryChoice===select.value));
  const picture=chosen&&characterPicture(chosen,'library');
  if(picture?.inline){image.src='data:image/png;base64,'+picture.inline;image.hidden=false}
  else if(picture?.path)file(picture.path).then(blob=>{if(current!==previewTicket||ticket!==characterRenderTicket)return;const url=URL.createObjectURL(blob);characterImageUrls.push(url);image.src=url;image.hidden=false}).catch(()=>{if(current===previewTicket&&ticket===characterRenderTicket&&!group.disabled&&!status.textContent)status.textContent='Vorschaubild nicht verfügbar.'});
  if(chosen)image.alt='Referenzbild von '+chosen.name;
 };
 apply.onclick=async()=>{
  const chosen=choices.find(c=>c.id===select.value);if(!chosen||storyPortraitBusy)return;
  if(chosen.id==='__original__'){
   if(!confirm('Ursprüngliches Profil und Referenzbilder wiederherstellen? Szenen und Gespräche bleiben erhalten. Anschließend die Geschichte speichern.'))return;
   try{editorPayload=restoreStoryCharacter({...editorPayload,scenes:gatherScenes()},character.id);drawScenes();markCharacterDirty();const card=Array.from($('story-characters').children).find(box=>box.dataset.characterId===character.id);if(card)card.open=true;message('Ursprüngliche Figur wiederhergestellt. Bitte die Geschichte speichern.')}catch(error){status.textContent=error.message}
   return;
  }

  if($('editor-mode').value!=='editorial'){status.textContent='Zuerst ein bearbeitbares Skript für die Geschichte erstellen.';return}
  if(!$('style').value){status.textContent='Zuerst einen Bildstil wählen, damit die Bibliotheksfigur als Comicfigur gezeichnet werden kann.';return}
  if(!confirm('„'+character.name+'“ durch „'+chosen.name+'“ aus der Bibliothek ersetzen? Aussehen, Eigenschaften und Referenzbilder werden übernommen. Der Name in der Geschichte bleibt erhalten. Szenen und Sprechblasen bleiben zugeordnet. Das Referenzbild wird anschließend im gewählten Comicstil neu gezeichnet und in dieser Geschichte gesichert.'))return;
  const current=editorPayload;group.disabled=true;storyPortraitBusy=true;updateWorkflowState();status.textContent='Profil und Referenzbilder werden übernommen …';
  try{
   const snapshot=await characterLibrarySnapshot(chosen);
   if(editorPayload!==current||!current.characters?.includes(character)||$('editor-mode').value!=='editorial')throw Error('Die Geschichte wurde inzwischen gewechselt. Bitte den Tausch erneut auswählen.');
   const next=replaceStoryCharacter({...current,scenes:gatherScenes()},character.id,snapshot);
   editorPayload=next;drawScenes();markCharacterDirty();
   const saved=await saveDefinition();
   message('Figur ersetzt. Das Bibliotheksfoto wird jetzt im gewählten Comicstil gezeichnet …');
   await convertLibraryPortrait(character.id,saved.id);
   message('Bibliotheksfigur als Comicfigur gezeichnet und gesichert. Das Bibliotheksoriginal bleibt erhalten.');
  }catch(problem){status.textContent=problem.message;error(problem)}finally{group.disabled=false;storyPortraitBusy=false;updateWorkflowState()}
 };
 const toolbar=document.createElement('div');toolbar.className='character-replacement-toolbar row';toolbar.append(label,apply);group.append(toolbar,image,status,gallery,note);return group;
}
function characterPicture(c,scope){
 if(scope==='story'&&editorPayload.reference_overrides?.[c.id]?.length)return {inline:editorPayload.reference_overrides[c.id][0]};
 if(c.inline_references?.length)return {inline:c.inline_references[0]};
 if(c.references?.length)return {path:'/characters/'+(c.reference_character_id||c.id)+'/references/'+c.references[0]};
 if(scope==='story'){const output=jobs.find(j=>j.story_id===definitionId&&j.artifacts?.some(a=>a.name==='characters/'+c.id+'.png'||a.name==='characters/'+c.id+'-0.png'));const item=output?.artifacts.find(a=>a.name==='characters/'+c.id+'.png'||a.name==='characters/'+c.id+'-0.png');if(item)return {path:item.url}}
 return null;
}
function drawCharacterEditor({preserveOpen=false}={}){
 const openIds=preserveOpen?new Set(Array.from($('story-characters').children).filter(card=>card.open).map(card=>card.dataset.characterId)):new Set();
 const ticket=++characterRenderTicket;characterPreviewObserver?.disconnect();for(const url of characterImageUrls)URL.revokeObjectURL(url);characterImageUrls=[];
 const cast=editorPayload.characters||[];$('story-characters').replaceChildren(...cast.map(c=>characterCard(c,'story',ticket)));
 for(const card of $('story-characters').children)if(openIds.has(card.dataset.characterId))card.open=true;
 $('story-character-empty').hidden=cast.length>0;
 $('library-characters').replaceChildren(...characterLibrary.map(c=>characterCard(c,'library',ticket)));
 refreshSpeechCastOptions();
 $('cast-summary').textContent=cast.length?'Figuren dieser Geschichte: '+cast.map(c=>c.name).join(' · '):'Noch keine Figuren in dieser Geschichte.';
}
function openCharacterPicture(image,name){if(image.hidden||!image.src)return;const dialog=$('character-picture-dialog');$('character-picture-title').textContent=name||'Figurenbild';$('character-picture-large').src=image.src;$('character-picture-large').alt='Referenzbild von '+(name||'Figur');if(!dialog.open)dialog.showModal()}
document.getElementById('character-picture-close').onclick=()=>document.getElementById('character-picture-dialog').close();
document.getElementById('character-picture-dialog').addEventListener('close',()=>document.getElementById('character-picture-large').removeAttribute('src'));
function characterCard(c,scope,ticket){
 const box=document.createElement('details');box.className='character-card';box.dataset.characterId=c.id;box.dataset.scope=scope;
 const heading=document.createElement('summary'),image=document.createElement('img'),name=document.createElement('strong'),placeholder=document.createElement('span');
 image.tabIndex=0;image.setAttribute('role','button');image.title='Figurenbild vergrößern';image.setAttribute('aria-label','Figurenbild vergrößern');image.onclick=e=>{e.preventDefault();e.stopPropagation();openCharacterPicture(image,c.name)};image.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();e.stopPropagation();openCharacterPicture(image,c.name)}};
 image.className='character-photo';image.alt='Referenzbild von '+c.name;image.hidden=true;name.textContent=c.name;placeholder.textContent='Kein Referenzbild';placeholder.className='character-placeholder';heading.append(image,name,placeholder);box.append(heading);
 const picture=characterPicture(c,scope);if(picture?.inline){image.src='data:image/png;base64,'+picture.inline;image.hidden=false;placeholder.hidden=true}else if(picture?.path){file(picture.path).then(blob=>{if(ticket!==characterRenderTicket)return;const url=URL.createObjectURL(blob);characterImageUrls.push(url);image.src=url;image.hidden=false;placeholder.hidden=true}).catch(()=>{placeholder.textContent='Referenzbild nicht verfügbar'})}
 const id=document.createElement('small');id.textContent='Figuren-ID: '+c.id;box.append(id);
 if(scope==='story')box.append(characterReplacementPicker(c,ticket));
 const controls=document.createElement('fieldset');controls.className='character-fields';box.append(controls);
 for(const [key,label,limit,tag] of characterFields){const l=document.createElement('label'),e=document.createElement(tag);l.append(document.createTextNode(label));e.value=c[key]||'';e.maxLength=limit;e.dataset.characterField=key;l.append(e);controls.append(l);e.oninput=event=>{event.stopPropagation();c[key]=e.value;if(key==='name'){name.textContent=e.value;image.alt='Referenzbild von '+e.value;refreshSpeechCastOptions()}if(scope==='story')markCharacterDirty();else status.textContent='Ungespeicherte Änderungen in der Bibliothek.'}}
 const alignLabel=document.createElement('label'),align=document.createElement('select');align.dataset.characterField='alignment';alignLabel.append(document.createTextNode('Gesinnung (freiwillig)'));for(const [value,label] of Object.entries(characterAlignments)){const o=document.createElement('option');o.value=value;o.textContent=label;align.append(o)}align.value=c.alignment||'';alignLabel.append(align);controls.append(alignLabel);
 align.oninput=event=>{event.stopPropagation();c.alignment=align.value;if(scope==='story')markCharacterDirty();else status.textContent='Ungespeicherte Änderungen in der Bibliothek.'};
 const hint=document.createElement('p');hint.textContent='Ordnung: rechtschaffen – neutral – chaotisch. Moral: gut – neutral – böse. „Nicht festgelegt“ lässt die Gesinnung offen und ist keine neutrale Gesinnung.';controls.append(hint);
 const uploadLabel=document.createElement('label'),upload=document.createElement('input');upload.type='file';upload.accept='image/png,image/jpeg,image/webp';uploadLabel.append(document.createTextNode('Referenzbild hochladen / ersetzen'),upload);controls.append(uploadLabel);
 upload.onchange=async event=>{event.stopPropagation();const f=upload.files[0];if(!f)return;try{const encoded=await normalizedCharacterImage(f);c.inline_references=[encoded];c.references=[];if(scope==='story'){if(editorPayload.reference_overrides)delete editorPayload.reference_overrides[c.id];markCharacterDirty()}image.src='data:image/png;base64,'+encoded;image.hidden=false;placeholder.hidden=true;status.textContent='Neues Referenzbild vorbereitet. Zum Übernehmen speichern.'}catch(e){status.textContent=e.message}finally{upload.value=''}};
 const options=document.createElement('label'),determine=document.createElement('input');determine.type='checkbox';determine.checked=Boolean(c.alignment);options.append(determine,document.createTextNode('Beim Neuerzeugen auch eine Gesinnung bestimmen'));controls.append(options);
 const row=document.createElement('div');row.className='row';controls.append(row);const status=document.createElement('p');status.className='character-status';status.setAttribute('role','status');box.append(status);
 const button=(label,handler)=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=handler;row.append(b);return b};
 button('Aussehen & Gesinnung neu erzeugen',async()=>{controls.disabled=true;status.textContent='Figurenauftrag wird vorbereitet …';try{const requested=await(await api('/characters/regenerate','POST',{profile:structuredClone(c),style:$('style').value,determine_alignment:determine.checked})).json();status.textContent='Neues Aussehen wartet auf die lokale Generierung …';let result;for(;;){await new Promise(resolve=>setTimeout(resolve,1800));result=await(await api('/characters/regenerations/'+requested.id)).json();if(['completed','failed'].includes(result.status))break;status.textContent=result.stage==='character_portrait'?'Neues Referenzbild wird lokal gezeichnet …':'Aussehen und Gesinnung werden lokal geplant …'}if(result.status==='failed')throw Error(result.error||'Figur konnte nicht erzeugt werden.');Object.assign(c,{description:result.profile.description,alignment:result.profile.alignment,inline_references:result.profile.inline_references,references:[]});if(scope==='story'&&editorPayload.characters?.includes(c)){if(editorPayload.reference_overrides)delete editorPayload.reference_overrides[c.id];markCharacterDirty()}if(ticket===characterRenderTicket){controls.querySelector('[data-character-field="description"]').value=c.description;align.value=c.alignment;image.src='data:image/png;base64,'+c.inline_references[0];image.hidden=false;placeholder.hidden=true}status.textContent='Neues Aussehen und Gesinnung bereit. ID, Name und Vorgeschichte bleiben erhalten. Zum Übernehmen speichern.'}catch(e){status.textContent=e.message}finally{controls.disabled=false}});
 if(scope==='story'){
 button('In Bibliothek speichern',async()=>{try{if(!characterLibraryLoaded)await loadCharacterLibrary();if(!characterLibraryLoaded)throw Error('Bibliothek zuerst laden.');const libraryId=c.library_source_id||c.id,old=characterLibrary.find(x=>x.id===libraryId);const saved=await(await api('/characters','POST',{...structuredClone(c),id:libraryId,version:old?.version||0})).json();characterLibrary=characterLibrary.filter(x=>x.id!==libraryId);characterLibrary.push(saved);drawCharacterEditor();message('Figur in der Bibliothek gespeichert. Die Geschichte separat speichern.')}catch(e){status.textContent=e.message}});
 button('Aus Geschichte löschen',()=>{if(!confirm('Figur aus dieser Geschichte löschen? Ihre Sprecherzuordnungen und Sprechblasen werden ebenfalls entfernt. Szenentexte danach prüfen. Die Bibliothek und erzeugte Comics bleiben erhalten.'))return;try{editorPayload.scenes=gatherScenes();editorPayload.characters=editorPayload.characters.filter(x=>x.id!==c.id);editorPayload.library_ids=(editorPayload.library_ids||[]).filter(x=>x!==c.id);for(const scene of editorPayload.scenes){scene.characters=(scene.characters||[]).filter(x=>x!==c.id);scene.bubbles=(scene.bubbles||[]).filter(b=>b.speaker!==c.id&&b.speaker!==c.name);if(scene.character_states)delete scene.character_states[c.id]}for(const key of ['reference_overrides','outfits'])if(editorPayload[key])delete editorPayload[key][c.id];if(editorPayload.narrator_character_id===c.id){delete editorPayload.narrator_character_id;editorPayload.narrator_badge=false}drawScenes();markCharacterDirty();message('Figur aus dem Entwurf entfernt. Szenentexte prüfen und speichern.')}catch(e){status.textContent=e.message}});
 }else{
 button('In diese Geschichte übernehmen',async()=>{try{if($('editor-mode').value!=='editorial')throw Error('Zum Bearbeiten einzelner Figuren die Arbeitsweise „Meinen Artikel in Szenen umsetzen“ wählen.');if((editorPayload.characters||[]).some(x=>x.id===c.id))throw Error('Diese Figur ist bereits in der Geschichte.');if((editorPayload.characters||[]).length>=8)throw Error('Maximal acht Figuren pro Geschichte.');const snapshot=await characterLibrarySnapshot(c);editorPayload.characters??=[];editorPayload.characters.push(snapshot);editorPayload.library_ids=(editorPayload.library_ids||[]).filter(x=>x!==c.id);drawCharacterEditor();markCharacterDirty();message('Figur als bearbeitbare Kopie übernommen. Geschichte speichern.')}catch(e){status.textContent=e.message}});
 button('Bibliotheksfigur speichern',async()=>{try{const saved=await(await api('/characters','POST',c)).json();Object.assign(c,saved);status.textContent='Bibliotheksfigur gespeichert. Bestehende Geschichten behalten ihre eigenen Figurenkopien.'}catch(e){status.textContent=e.message}});
 button('Aus Bibliothek löschen',async()=>{if(!confirm('Figur aus der Bibliothek löschen? Bestehende Geschichten und Comics behalten ihre Figurenkopien und Bilder.'))return;try{await api('/characters/'+c.id,'DELETE',{version:c.version});characterLibrary=characterLibrary.filter(x=>x.id!==c.id);drawCharacterEditor();message('Figur aus der Bibliothek gelöscht.')}catch(e){status.textContent=e.message}});
 }
 return box;
}
async function blobBase64(blob){return await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=()=>reject(Error('Bild konnte nicht gelesen werden.'));r.readAsDataURL(blob)})}
async function normalizedCharacterImage(file){if(file.size>12*1024*1024)throw Error('Referenzbild maximal 12 MB.');if(!['image/png','image/jpeg','image/webp'].includes(file.type))throw Error('PNG, JPEG oder WebP verwenden.');const image=await createImageBitmap(file);try{if(image.width*image.height>25000000)throw Error('Referenzbild maximal 25 Megapixel.');const scale=Math.min(1,1536/image.width,1536/image.height),canvas=document.createElement('canvas');canvas.width=Math.round(image.width*scale);canvas.height=Math.round(image.height*scale);canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);const result=canvas.toDataURL('image/png').split(',')[1];if(result.length>8000000)throw Error('Referenzbild nach Aufbereitung zu groß.');return result}finally{image.close()}}

// Erstmalige Referenzbilder zeichnen, ohne Figurenprofile neu zu erfinden.
let storyPortraitBusy=false;
function updatePortraitButton(){
 const button=$('generate-portraits');if(!button)return;
 const missing=(editorPayload.characters||[]).filter(c=>!characterPicture(c,'story'));
 button.disabled=storyPortraitBusy||!$('style').value||!(editorPayload.characters||[]).length||!!planningJob;
 button.textContent=storyPortraitBusy?'Figuren werden generiert …':missing.length?'Figuren generieren · '+missing.length+' ohne Bild':'Figuren neu generieren';
 if(!storyPortraitBusy)$('portrait-progress').textContent=!$('style').value?'Zuerst einen Bildstil wählen.':missing.length?'Erstellt nur fehlende Referenzbilder. Namen, Aussehen, Vorgeschichte und Gesinnung bleiben erhalten.':(editorPayload.characters?.length?'Alle Figuren haben Bilder. Du kannst ihre Referenzbilder im gewählten Stil neu generieren.':'Noch keine Figuren vorhanden.');
}
async function generateStoryPortraits(){
 if(storyPortraitBusy||!$('style').value||!editorPayload.characters?.length)return;
 const regenerateAll=editorPayload.characters.every(c=>characterPicture(c,'story'));
 if(regenerateAll&&!confirm('Alle Figurenbilder im gewählten Stil neu generieren und in dieser Geschichte ersetzen? Namen, Beschreibungen, Kleidung, Vorgeschichten und Gesinnungen bleiben erhalten. Fertige Comics und Bibliotheksfiguren bleiben unverändert.'))return;
 storyPortraitBusy=true;updateWorkflowState();
 let completed=0;
 try{
  const saved=await saveDefinition(),storyId=saved.id,style=$('style').value;
  const missing=(editorPayload.characters||[]).filter(c=>regenerateAll||!characterPicture(c,'story')).map(c=>c.id);
  for(const id of missing){
   const character=editorPayload.characters.find(c=>c.id===id),version=definitionVersion;
   if(definitionId!==storyId||dirty||!character)throw Error('Geschichte geändert. Bereits gesicherte Figurenbilder bleiben erhalten.');
   const snapshot=structuredClone(character);
   $('portrait-progress').textContent='Figur '+(completed+1)+' von '+missing.length+': '+character.name+' · Auftrag vorbereiten …';
   const work=await(await api('/characters/regenerate','POST',{profile:snapshot,style,portrait_only:true,use_reference:true,determine_alignment:false})).json();
   let result;
   do{
    result=await(await api('/characters/regenerations/'+work.id)).json();
    if(['queued','running'].includes(result.status)){
     $('portrait-progress').textContent='Figur '+(completed+1)+' von '+missing.length+': '+character.name+(result.status==='queued'?' · wartet …':' · Referenzbild wird gezeichnet …');
     await new Promise(resolve=>setTimeout(resolve,1800));
    }
   }while(['queued','running'].includes(result.status));
   if(result.status!=='completed')throw Error(result.error||'Figurenbild fehlgeschlagen.');
   const current=editorPayload.characters?.find(c=>c.id===id);
   if(definitionId!==storyId||definitionVersion!==version||dirty||JSON.stringify(current)!==JSON.stringify(snapshot))throw Error('Geschichte zwischenzeitlich bearbeitet. Das neue Bild wurde nicht darübergeschrieben; es liegt im Figurenauftrag '+work.id+'.');
   if(!result.profile?.inline_references?.length)throw Error('Der Figurenauftrag enthält kein Referenzbild.');
   current.inline_references=result.profile.inline_references;current.references=[];if(editorPayload.reference_overrides)delete editorPayload.reference_overrides[id];dirty=true;
   await saveDefinition();completed++;
  }
  message(completed+' Figurenbilder generiert und in dieser Geschichte gesichert. Kein Comic gestartet.');
 }catch(e){error(e)}finally{storyPortraitBusy=false;updateWorkflowState()}
}

async function convertLibraryPortrait(characterId,storyId){
 const character=editorPayload.characters.find(c=>c.id===characterId),snapshot=structuredClone(character),version=definitionVersion;
 const work=await(await api('/characters/regenerate','POST',{profile:snapshot,style:$('style').value,portrait_only:true,use_reference:true,determine_alignment:false})).json();
 let result;
 do{
  result=await(await api('/characters/regenerations/'+work.id)).json();
  if(['queued','running'].includes(result.status)){$('portrait-progress').textContent=character.name+(result.status==='queued'?' · Comic-Referenzbild wartet …':' · Foto wird als Comicfigur gezeichnet …');await new Promise(resolve=>setTimeout(resolve,1800))}
 }while(['queued','running'].includes(result.status));
 if(result.status!=='completed')throw Error(result.error||'Umwandlung zum Comic-Referenzbild fehlgeschlagen. Das übernommene Profil bleibt gesichert.');
 const current=editorPayload.characters?.find(c=>c.id===characterId);
 if(definitionId!==storyId||definitionVersion!==version||dirty||JSON.stringify(current)!==JSON.stringify(snapshot))throw Error('Geschichte zwischenzeitlich geändert. Comicbild bleibt im Figurenauftrag '+work.id+' erhalten; deine Änderungen wurden nicht überschrieben.');
 if(!result.profile?.inline_references?.length)throw Error('Kein Comic-Referenzbild zurückgegeben.');
 current.inline_references=result.profile.inline_references;current.references=[];if(editorPayload.reference_overrides)delete editorPayload.reference_overrides[characterId];dirty=true;
 await saveDefinition();
}
