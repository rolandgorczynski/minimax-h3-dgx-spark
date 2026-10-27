/* Vier getrennte Arbeitsschritte; Navigation verändert keine gespeicherten Daten. */
let workflowInstalled=false,workflowStep='script',workflowOutput=null;
function showWorkflowStep(step){
 if(!['script','render','edit','publish'].includes(step))return;
 workflowStep=step;if(step==='publish')loadPublishProfiles();
 for(const value of ['script','render','edit','publish'])$('workflow-'+value).hidden=value!==step;
 for(const button of document.querySelectorAll('[data-workflow-step]'))button.setAttribute('aria-current',button.dataset.workflowStep===step?'step':'false');
 updateWorkflowState();$('workflow-navigation').scrollIntoView({behavior:'smooth',block:'start'});
}
let publishProfileDirty={},publishProfileLoading=false,publishProfileSaving=false;
async function loadPublishProfiles(){
 if(publishProfileLoading)return;publishProfileLoading=true;
 const results=await Promise.allSettled([api('/sharing').then(r=>r.json()),api('/telegram-publishing').then(r=>r.json())]);
 for(const platform of ['x','substack','telegram']){
  const result=results[platform==='telegram'?1:0],field=$('publish-'+platform+(platform==='telegram'?'-channel':'-url'));
  if(publishProfileDirty[platform])continue;
  if(result.status==='fulfilled'){
   field.value=platform==='telegram'?result.value.target?.channel||'':result.value[platform+'_url']||'';
   $('publish-'+platform+'-status').textContent=field.value?'Gespeicherter Standard. Änderbar für deine nächsten Veröffentlichungen.':'Noch kein Standard angegeben.';
   $('publish-'+platform+'-save').disabled=true;
  }else $('publish-'+platform+'-status').textContent='Standard konnte nicht geladen werden: '+result.reason.message;
 }
 publishProfileLoading=false;
}
async function savePublishProfile(platform){
 if(publishProfileSaving)return;
 const field=$('publish-'+platform+(platform==='telegram'?'-channel':'-url')),button=$('publish-'+platform+'-save'),status=$('publish-'+platform+'-status');
 if(platform!=='telegram'&&!field.reportValidity())return;
 const value=field.value.trim();publishProfileSaving=true;for(const target of ['x','substack','telegram'])$('publish-'+target+'-save').disabled=true;
 try{
  if(platform==='telegram'){
   status.textContent='Kanal und Bot-Berechtigung werden geprüft …';
   const result=await(await api('/telegram-publishing','PUT',{channel:value})).json();
   if(field.value.trim()===value){field.value=result.target?.channel||value;publishProfileDirty[platform]=false}
  }else{
   // Aktuelle andere Plattform beibehalten, auch wenn sie zwischenzeitlich im Teilen-Dialog geändert wurde.
   const targets=await(await api('/sharing')).json();
   await api('/sharing','PUT',{...targets,[platform+'_url']:value});
   if(field.value.trim()===value){field.value=value;publishProfileDirty[platform]=false}
  }
  status.textContent=publishProfileDirty[platform]?'Standard gespeichert. Weitere Änderungen im Feld sind noch nicht gespeichert.':'Als Standard gespeichert. Wird bei kommenden Veröffentlichungen vorbelegt. Noch nichts veröffentlicht.';
 }catch(e){status.textContent=e.message}
 finally{publishProfileSaving=false;for(const target of ['x','substack','telegram'])$('publish-'+target+'-save').disabled=!publishProfileDirty[target]}
}
function installPublishProfiles(){
 for(const platform of ['x','substack','telegram']){
  $('publish-'+platform+(platform==='telegram'?'-channel':'-url')).oninput=()=>{publishProfileDirty[platform]=true;$('publish-'+platform+'-save').disabled=publishProfileSaving;$('publish-'+platform+'-status').textContent='Geändert, noch nicht als Standard gespeichert.'};
  $('publish-'+platform+'-save').onclick=()=>savePublishProfile(platform);
 }
}
function showWorkflowInput(input){
 showWorkflowStep('script');
 for(const value of ['own','source','series'])$('workflow-'+value+'-slot').hidden=value!==input;
 for(const button of document.querySelectorAll('[data-script-input]'))button.setAttribute('aria-pressed',String(button.dataset.scriptInput===input));
 if(input==='source')$('source-generator').open=true;
 if(input==='series')$('series-editor').open=true;
}
function updateWorkflowState(){
 if(!workflowInstalled)return;
 const selector=$('render-story-list');selector.replaceChildren(new Option('Skript auswählen',''),...definitions.filter(doc=>$('render-show-unfinished').checked||doc.script_ready===true||doc.id===definitionId).map(doc=>new Option(doc.name+(doc.script_ready===false?' · Skript offen':''),doc.id)));selector.value=definitionId;
 const ready=$('editor-mode').value==='editorial'&&!needsPlan()&&!planningJob;
 const previous=editorPayload.planned_count??editorPayload.scenes?.length??0,current=Number($('count').value);
 const changed=previous>0&&current!==previous,valid=Number.isSafeInteger(current)&&current>0;
 $('count-replan').disabled=$('editor-mode').value!=='editorial'||!!planningJob||!changed||!valid;
 $('count-change-hint').textContent=changed&&valid?'Kachelanzahl geändert: '+previous+' → '+current+'. Skript neu erstellen, bevor du Bilder erzeugst. Bestehende Comics bleiben erhalten.':'';
 $('script-to-render').disabled=!ready;
 $('render-comic').disabled=!ready||!$('style').value;
 $('workflow-render-summary').textContent=($('story-name').value||'Noch kein Skript gewählt')+' · '+$('count').value+' Kacheln · '+(planningJob?'Skript wird erstellt':ready?'Skript bereit':'Skript zuerst in Schritt 1 erstellen oder aktualisieren');
 $('workflow-render-status').textContent=ready?(!$('style').value?'Bildstil auswählen. Danach kannst du den Comic erzeugen.':'Stil und Seitenvorlage gelten für die nächste Ausgabe. Vorhandene Comics bleiben erhalten.'):'Hier werden keine neuen Szenen geplant. Bitte zuerst das Skript in Schritt 1 fertigstellen.';
 updateWorkflowOutput(workflowOutput);
}
function updateWorkflowOutput(job){
 workflowOutput=job;
 const area=$('workflow-publish-summary');if(!area)return;
 const title=$('title')?.textContent||job?.story_title||'Comic';
 area.textContent=job?title+' · Ausgabe '+job.id.slice(0,8)+' · '+(typeof stateNames!=='undefined'?stateNames[job.status]||job.status:job.status)+'. Veröffentlicht oder exportiert wird diese ausgewählte Ausgabe.':'Zuerst in Schritt 3 eine fertige Comic-Ausgabe auswählen.';
 const latest=job&&outputGroups().find(g=>g.some(j=>j.id===job.id))?.[0];if(latest&&latest.id!==job.id)area.textContent+=' Achtung: Du hast eine ältere Fassung ausgewählt. Eine neuere Ausgabe ist in Schritt 3 verfügbar.';
 if(job?.story_id===definitionId&&(dirty||job.story_version!==definitionVersion))area.textContent+=' Skript oder Gestaltung wurden inzwischen bearbeitet. Diese Ausgabe zeigt ihren gespeicherten Stand; neuere Änderungen erfordern eine neue Comic-Ausgabe.';
 $('edit-to-publish').disabled=!job||!job.artifacts?.some(a=>a.name==='comic.png');
}
/* Ausgaben pro Geschichte; Abruf alter Vorfahren ausschließlich lesend. */
const outputHistoryCache=new Map();
function outputKind(job){return job.panel_correction_mode?'Bild '+job.corrected_panel+' neu gezeichnet':job.lettering_mode?'Beschriftung geändert':job.experiment_mode?'Experiment':job.improvement_mode?'Nach Rückmeldung überarbeitet':'Comic erzeugt'}
function outputDate(job){return job.created_at&&!Number.isNaN(Date.parse(job.created_at))?new Date(job.created_at).toLocaleString('de-DE',{dateStyle:'short',timeStyle:'short'}):job.id.slice(0,8)}
function outputGroups(){
 const byId=new Map(jobs.map(j=>[j.id,j])),groups=new Map();
 for(const job of jobs){
  let root=job,seen=new Set();
  while(root.parent_job&&byId.has(root.parent_job)&&!seen.has(root.id)){seen.add(root.id);root=byId.get(root.parent_job)}
  const key=job.story_id||root.story_id||root.id;
  if(!groups.has(key))groups.set(key,[]);groups.get(key).push(job);
 }
 for(const group of groups.values())group.sort((a,b)=>{
  const x=Date.parse(a.created_at),y=Date.parse(b.created_at);
  return Number.isFinite(x)&&Number.isFinite(y)?y-x:jobs.indexOf(a)-jobs.indexOf(b);
 });
 return Array.from(groups.values());
}
function renderOutputSelection(){
 for(const [id,job]of outputHistoryCache)if(!jobs.some(j=>j.id===id))jobs.push(job);
 const groups=outputGroups();if(!jobs.some(j=>j.id===selected))selected=groups[0]?.[0]?.id||'';
 const all=$('output-show-history').checked,selector=$('jobs');selector.replaceChildren();
 for(const group of groups){
  const section=document.createElement('optgroup'),first=group[0],story=definitions.find(d=>d.id===first.story_id);
  section.label=story?.name||first.story_title||'Comic '+first.id.slice(0,8);
  for(const job of group){
   if(!all&&job!==first&&job.id!==selected)continue;
   const label=(job===first?'Neueste Ausgabe':'Frühere Fassung')+' · '+outputKind(job)+' · '+(stateNames[job.status]||job.status)+' · '+outputDate(job)+' · '+job.id.slice(0,8);
   section.append(new Option(label,job.id));
  }
  selector.append(section);
 }
 selector.value=selected;
}
async function chooseOutput(id){
 if(!id)return;
 if(!jobs.some(j=>j.id===id)){const job=await(await api('/jobs/'+id)).json();outputHistoryCache.set(id,job);jobs.push(job)}
 selected=id;loaded='';renderOutputSelection();await show();
}
async function openOutputOriginal(){
 let job=jobs.find(j=>j.id===selected),seen=new Set();if(!job)return;
 while(job.parent_job){
  if(seen.has(job.id))throw Error('Der Ausgabenverlauf enthält einen ungültigen Kreis.');seen.add(job.id);
  let parent=jobs.find(j=>j.id===job.parent_job);
  if(!parent){parent=await(await api('/jobs/'+job.parent_job)).json();outputHistoryCache.set(parent.id,parent);jobs.push(parent)}
  job=parent;
 }
 await chooseOutput(job.id);
}
function updateOutputHistory(job){
 const group=job&&outputGroups().find(g=>g.some(j=>j.id===job.id)),latest=group?.[0];
 $('output-current').textContent=job?'Ausgewählte Ausgabe: '+job.id.slice(0,8)+' · '+outputKind(job)+' · '+outputDate(job)+(latest?.id!==job.id?' · Ältere Fassung ausgewählt.':' · Neueste Ausgabe dieser Geschichte.'):'Noch keine Comic-Ausgabe ausgewählt.';
 $('output-prev').disabled=!job?.parent_job;$('output-original').disabled=!job?.parent_job;$('output-latest').disabled=!latest||latest.id===job?.id;
 $('output-prev').onclick=()=>chooseOutput(job?.parent_job).catch(error);
 $('output-original').onclick=()=>openOutputOriginal().catch(error);
 $('output-latest').onclick=()=>chooseOutput(latest?.id).catch(error);
 const list=$('output-history-list');list.replaceChildren();
 for(const item of group||[]){const li=document.createElement('li'),b=document.createElement('button');b.type='button';b.textContent=(item.id===job.id?'Ausgewählt · ':'')+outputKind(item)+' · '+outputDate(item)+' · '+item.id.slice(0,8);b.disabled=item.id===job.id;b.onclick=()=>chooseOutput(item.id).catch(error);li.append(b);list.append(li)}
}
async function openOutputEditor(index=0,jobId=selected){
 try{
  if(selected!==jobId)await chooseOutput(jobId);
  await $('lettering-edit').onclick();
  if(positionData?.job_id===jobId)await showPositionPanel(Math.max(0,Math.min(index,positionData.panels.length-1)));
 }catch(e){error(e)}
}
function drawOutputWarnings(job){
 const letters=$('lettering-issues');letters.replaceChildren();
 const messages=(job.lettering_warnings||[]).filter(t=>!/^ENTWURF:/i.test(t));
 if(job.lettering_unresolved&&!messages.length)messages.push('Eine Beschriftung muss geprüft werden. Vollständige Texte sind im Editor erhalten.');
 function item(text){const li=document.createElement('li');li.append(document.createTextNode(text+' '));const number=text.match(/(?:Kachel|Bild|Panel)\s*(\d+)\s*:/i);if(number){const b=document.createElement('button');b.type='button';b.textContent='Dort bearbeiten';b.dataset.issuePanel=number[1];b.onclick=()=>openOutputEditor(Number(number[1])-1,job.id);li.append(b)}return li}
 for(const text of messages)letters.append(item(text));
 const equipment=$('equipment-warning');equipment.replaceChildren();
 if(job.equipment_warnings?.length){const title=document.createElement('strong');title.textContent='Bilddetails prüfen';const list=document.createElement('ul');for(const text of job.equipment_warnings)list.append(item(text));equipment.append(title,list)}
}

function installWorkflowUI(){
 const source=$('source-generator').closest('section'),series=$('series-editor').closest('section');
 $('workflow-own-slot').append($('verwaltung'));$('workflow-source-slot').append(source);$('workflow-series-slot').append(series);
 $('workflow-story-selection').append($('story-selection'));
 $('workflow-visual-settings').append($('render-style-controls'),$('page-template-picker'));
 $('workflow-character-settings').append($('character-design-controls'));
 $('workflow-output-selection').append($('output-selection'));
 $('workflow-output-content').append($('output-editor'));
 for(const id of ['bundle','pdf','substack-share','x-share','telegram-share'])$('workflow-share-actions').append($(id));
 $('workflow-book-export').append($('book-exporter'));
 $('advanced').append($('next').closest('details'));
 for(const id of ['comment','learning-status'])$('workflow-feedback').append($(id).closest('section'));
 for(const button of document.querySelectorAll('[data-workflow-step]'))button.onclick=()=>showWorkflowStep(button.dataset.workflowStep);
 for(const button of document.querySelectorAll('[data-script-input]'))button.onclick=()=>showWorkflowInput(button.dataset.scriptInput);
 $('script-to-render').onclick=async()=>{try{if(needsPlan())throw Error('Skript zuerst aktualisieren.');if(dirty||!definitionId)await saveDefinition();showWorkflowStep('render')}catch(e){error(e)}};
 $('render-show-unfinished').onchange=updateWorkflowState;
 $('render-story-list').onchange=async()=>{const id=$('render-story-list').value;if(!id)return;if(dirty&&!confirm('Ungespeicherte Änderungen verwerfen?')){$('render-story-list').value=definitionId;return}try{fillDefinition(await(await api('/stories/'+id)).json());showWorkflowStep('render')}catch(e){error(e)}};
 $('render-back-to-script').onclick=()=>showWorkflowInput('own');
 $('edit-to-publish').onclick=()=>showWorkflowStep('publish');$('publish-back-to-edit').onclick=()=>showWorkflowStep('edit');
 $('render-save').onclick=async()=>{try{await saveDefinition();message('Gestaltung gespeichert. Kein Comic-Lauf gestartet.')}catch(e){error(e)}};
 $('render-comic').onclick=async()=>{
  if(needsPlan()||planningJob){showWorkflowInput('own');message('Skript zuerst in Schritt 1 fertigstellen.');return}
  if(!$('style').value){message('Zuerst einen Bildstil wählen.');return}
  $('render-comic').disabled=true;
  try{const doc=await saveDefinition();const job=await(await api('/stories/'+doc.id+'/generate','POST',{version:doc.version})).json();selected=job.id;loaded='';showWorkflowStep('edit');message('Comic wird aus dem gespeicherten Skript erzeugt. Bisherige Ausgaben bleiben erhalten.');await list()}catch(e){error(e)}finally{updateWorkflowState()}
 };
 $('workflow-render').addEventListener('input',event=>{if(['render-story-list','render-show-unfinished','page-template-category'].includes(event.target.id))return;dirty=true;$('definition-state').textContent='Ungespeicherte Änderungen';modeHelp()});
 $('style').addEventListener('change',()=>{editorPayload.visual_style_pending=!$('style').value;dirty=true;modeHelp()});
 $('new').addEventListener('click',()=>{if(!definitionId&&!dirty)showWorkflowInput('own')});
 $('story-list').addEventListener('change',()=>showWorkflowInput('own'));
 $('output-show-history').onchange=()=>{renderOutputSelection();updateOutputHistory(jobs.find(j=>j.id===selected))};
 installPublishProfiles();workflowInstalled=true;showWorkflowInput('own');
}
document.addEventListener('DOMContentLoaded',installWorkflowUI);
