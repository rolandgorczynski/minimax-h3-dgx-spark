/* Quellen → lokales Skript → geprüfte Geschichte. Bilder erst auf ausdrücklichen Klick. */
let sourceEntries=[],sourceSelected='',sourceTask='',sourceTimer=null,sourceScriptDirty=false,sourceBusy=false,sourcePostDirty=false,sourceTaskSourceId='';
const sourceFields=['title','kind','creator','edition','url','territories','rights','text','post_summary','category'];
function sourceSearchKey(value){return value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('de').replace(/ß/g,'ss')}
function sourceDraftChanged(){const entry=sourceEntries.find(s=>s.id===sourceSelected)||{};return sourceFields.some(k=>$('source-'+k).value!==(entry[k]??(k==='kind'?'Buch':'')))}
function sourceSearchMatches(entry,words){return words.every(w=>sourceSearchKey([entry.title,entry.creator,entry.edition,entry.category,entry.collection,entry.post_summary].join(' ')).includes(w))}
function sourceFilterOptions(){
 const selected={category:$('source-category-filter').value,collection:$('source-collection-filter').value};
 const words=sourceSearchKey($('source-search').value).trim().split(/\s+/).filter(Boolean);
 for(const [field,label] of [['category','Alle Kategorien'],['collection','Alle Sammlungen']]){
  const select=$('source-'+field+'-filter'),old=selected[field],other=field==='category'?'collection':'category';
  const counts=new Map(sourceEntries.map(entry=>[entry[field]||'Nicht zugeordnet',0]));
  for(const entry of sourceEntries){
   if((!selected[other]||entry[other]===selected[other])&&sourceSearchMatches(entry,words)){
    const value=entry[field]||'Nicht zugeordnet';counts.set(value,counts.get(value)+1);
   }
  }
  const total=[...counts.values()].reduce((sum,count)=>sum+count,0);
  select.replaceChildren(new Option(label+' ('+total+')',''),...[...counts].sort((a,b)=>a[0].localeCompare(b[0],'de')).map(([value,count])=>new Option(value+' ('+count+')',value)));
  if(counts.has(old))select.value=old;
 }
 $('source-category-options').replaceChildren(...[...new Set(sourceEntries.map(s=>s.category).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'de')).map(s=>new Option(s,s)));
}
function renderSourceOptions(){
 sourceFilterOptions();
 const category=$('source-category-filter').value,collection=$('source-collection-filter').value;
 const words=sourceSearchKey($('source-search').value).trim().split(/\s+/).filter(Boolean);
 const matches=sourceEntries.filter(s=>(!category||s.category===category)&&(!collection||s.collection===collection)&&sourceSearchMatches(s,words));
 const select=$('source-select');select.replaceChildren(new Option('Neue Quelle anlegen',''));
 const current=sourceEntries.find(s=>s.id===sourceSelected),pinned=current&&!matches.some(s=>s.id===sourceSelected);
 if(pinned){const group=document.createElement('optgroup');group.label='Aktuell geöffnet · außerhalb des Filters';group.append(new Option(current.title,current.id));select.append(group)}
 const groups=new Map();
 for(const entry of [...matches].sort((a,b)=>a.title.localeCompare(b.title,'de'))){const key=entry.category||'Nicht zugeordnet';if(!groups.has(key))groups.set(key,[]);groups.get(key).push(entry)}
 for(const [label,entries] of [...groups].sort((a,b)=>a[0].localeCompare(b[0],'de'))){const group=document.createElement('optgroup');group.label=label;group.append(...entries.map(s=>new Option(s.title+' · '+s.kind,s.id)));select.append(group)}
 select.value=sourceSelected;
 $('source-result-count').textContent=matches.length+' passende Vorlagen von '+sourceEntries.length+(pinned?' · Die aktuell geöffnete Vorlage bleibt zusätzlich ausgewählt.':matches.length?'':' · Filter oder Suchbegriff ändern.');
}
function sourceMessage(t){$('source-status').textContent=t}
function fillSource(id){sourcePostDirty=false;sourceSelected=id;const entry=sourceEntries.find(s=>s.id===id)||{};for(const k of sourceFields)$('source-'+k).value=entry[k]??(k==='kind'?'Buch':'');renderSourceOptions();$('source-rights-summary').textContent=entry.id?'Ausgabe: '+(entry.edition||'nicht angegeben')+' · Absatzländer: '+(entry.territories||'nicht angegeben')+'\nRechtehinweis: '+(entry.rights||'Noch nicht erfasst.'):'';}
async function loadSources(){try{const preserveDraft=sourceEntries.length>0&&sourceDraftChanged();sourceEntries=(await(await api('/sources')).json()).sources;sourceFilterOptions();if(preserveDraft)renderSourceOptions();else fillSource(sourceEntries.some(s=>s.id===sourceSelected)?sourceSelected:sourceEntries[0]?.id||'');const saved=localStorage.getItem('comic-source-task');if(saved&&!sourceTask){sourceTask=saved;pollSourceTask(saved,true)}}catch(e){sourceMessage(e.message)}}
async function pollSourceTask(id,restore=false){if(sourceTask!==id)return;try{const job=await(await api('/source-tasks/'+id)).json();if(sourceTask!==id)return;sourceTaskSourceId=job.source_input?.source.id||'';if(restore&&job.source_input){const input=job.source_input;if(sourceEntries.some(s=>s.id===input.source.id))fillSource(input.source.id);$('source-count').value=job.request.kacheln;$('source-author').value=input.author||'';$('source-instructions').value=input.instructions||'';}if(['queued','running'].includes(job.status)){sourceBusy=true;$('source-create').disabled=true;sourceMessage(job.status==='queued'?'Skriptauftrag wartet …':job.stage==='source_outline'?'Figuren und Handlungsbogen werden lokal geplant …':job.stage==='script_continuity'?'Zustände und Übergänge prüfen: '+(job.planned_panels??0)+' / '+job.request.kacheln:job.stage==='source_check'?'Szenen und Lesbarkeit werden geprüft …':'Kacheln werden lokal geschrieben und sprachlich geprüft … '+(job.planned_panels??0)+' / '+job.request.kacheln);sourceTimer=setTimeout(()=>pollSourceTask(id),2000);return}sourceBusy=false;$('source-create').disabled=false;if(job.status==='failed'){sourceMessage('Skripterstellung fehlgeschlagen: '+job.error);return}if(!sourcePostDirty&&sourceSelected===sourceTaskSourceId&&job.post_summary){$('source-post_summary').value=job.post_summary}if(!sourceScriptDirty)$('source-script').value=job.script;$('source-draft').hidden=false;$('source-adopt').disabled=false;sourceMessage('Skript bereit. Bearbeite es hier und übernimm es anschließend als neue Geschichte. Noch keine Bilder erzeugt.'+(job.source_issues?.length?'\nPrüfhinweise: '+job.source_issues.map(x=>'Kachel '+x.panel+': '+x.message).join('\n'):''));}catch(e){sourceBusy=false;$('source-create').disabled=false;sourceMessage(e.message)}}
function installSourceGenerator(){
 $('source-category-filter').onchange=renderSourceOptions;
 $('source-collection-filter').onchange=renderSourceOptions;
 $('source-search').oninput=renderSourceOptions;
 $('source-reload').onclick=()=>loadSources();
 $('source-post_summary').oninput=()=>{sourcePostDirty=true};
 $('source-select').onchange=()=>fillSource($('source-select').value);
 $('source-new').onclick=()=>{fillSource('');$('source-data').open=true;sourceMessage('Neue Quelle ausfüllen und speichern. Für Filme die konkret verwendete Fassung und Handlung erfassen.');};
 $('source-save').onclick=async()=>{try{const value=Object.fromEntries(sourceFields.map(k=>[k,$('source-'+k).value]));if(sourceSelected)value.id=sourceSelected;const result=await(await api('/sources','POST',value)).json();sourceSelected=result.id;const index=sourceEntries.findIndex(s=>s.id===result.id);if(index>=0)sourceEntries[index]=result;else sourceEntries.push(result);fillSource(result.id);await loadSources();sourceMessage('Quelle gespeichert. Noch kein Skript- oder Bildlauf gestartet.')}catch(e){sourceMessage(e.message)}};
 $('source-create').onclick=async()=>{if(sourceBusy)return;if(!sourceSelected){sourceMessage('Zuerst eine Quelle speichern.');return}if(!$('source-count').reportValidity())return;const entry=sourceEntries.find(s=>s.id===sourceSelected);if(sourceFields.filter(k=>k!=='post_summary').some(k=>$('source-'+k).value!==(entry[k]||''))){sourceMessage('Geänderte Quellendaten zuerst speichern.');return}sourceBusy=true;$('source-create').disabled=true;try{const job=await(await api('/source-tasks','POST',{source_id:sourceSelected,count:Number($('source-count').value),author:$('source-author').value,instructions:$('source-instructions').value})).json();sourceTask=job.id;localStorage.setItem('comic-source-task',job.id);sourceScriptDirty=false;$('source-script').value='';$('source-draft').hidden=true;clearTimeout(sourceTimer);pollSourceTask(job.id)}catch(e){sourceBusy=false;$('source-create').disabled=false;sourceMessage(e.message)}};
 $('source-script').oninput=()=>{sourceScriptDirty=true;sourceMessage('Skript bearbeitet. Beim Übernehmen werden die Figuren, Dialoge und Kachelgrenzen aus diesem Text geprüft.');};
 $('source-script-save').onclick=async()=>{if(!sourceTask)return;try{await api('/source-tasks/'+sourceTask+'/script','PUT',{script:$('source-script').value});sourceScriptDirty=false;sourceMessage('Bearbeitetes Skript gespeichert. Es wurden keine Bilder erzeugt.')}catch(e){sourceMessage(e.message)}};
 $('source-download').onclick=()=>downloadFile(new Blob([$('source-script').value],{type:'text/plain;charset=utf-8'}),'comic-skript.txt');
 $('source-adopt').onclick=async()=>{if(!sourceTask)return;if(dirty&&!confirm('Ungespeicherte Änderungen an der aktuell geöffneten Geschichte verwerfen?'))return;$('source-adopt').disabled=true;try{const story=await(await api('/source-tasks/'+sourceTask+'/adopt','POST',{script:$('source-script').value,...(sourceSelected===sourceTaskSourceId?{post_summary:$('source-post_summary').value}:{})})).json();await refreshStories();fillDefinition(story);if(typeof showWorkflowStep==='function')showWorkflowStep('render');else $('verwaltung').scrollIntoView({behavior:'smooth'});message('Quellenskript als neue Geschichte übernommen. Figuren, Szenen und Sprechblasen sind bereits vorhanden. In Schritt 2 Stil, Seitenvorlage und Figurenreferenzen wählen, dann „Comic erzeugen“ klicken.');sourceMessage('Als neue Geschichte übernommen: '+story.name+'. Das Originalskript und andere Geschichten bleiben erhalten.')}catch(e){sourceMessage(e.message)}finally{$('source-adopt').disabled=false}};
 $('source-generator').addEventListener('toggle',()=>{if($('source-generator').open&&!sourceEntries.length)loadSources()});
}
