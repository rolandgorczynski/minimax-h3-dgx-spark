/* Erzählkern und Umfang vorschlagen; Änderungen an der Kachelanzahl nur auf Klick. */
const meaningViews=new Map();
function meaningInput(kind){return kind==='source'?{text:$('source-text').value,instructions:$('source-instructions').value,count:Number($('source-count').value),identity:sourceSelected}:{text:$('article').value,instructions:'',count:Number($('count').value),identity:definitionId}}
function meaningSignature(kind){const {count,...value}=meaningInput(kind);return JSON.stringify(value)}
function showMeaning(kind,value){
 const state=meaningViews.get(kind);if(!state)return;
 state.value=value;state.output.replaceChildren();if(!value){state.output.hidden=true;return}state.output.hidden=false;
 const add=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;state.output.append(el);return el};
 if(value.central_question){add('h4','Die menschliche Grundfrage');add('p',value.central_question)}
 add('h4',(value.meaning_type||'Pointe')+' / Kernaussage');add('p',value.core);
 add('strong','Warum diese Deutung?');
 const list=add('ol','');for(const step of value.evidence?.length?value.evidence.map(e=>e.event+' → '+e.meaning):value.causal_chain){const li=document.createElement('li');li.textContent=step;list.append(li)}
 if(value.review_method==='redaktionell')add('small','Redaktionell ausgewertet.');
 add('p','Schlusswirkung: '+value.ending);
 add('p','Vorschlag für den vollständigen Einzelcomic: '+value.recommended_count+' Kacheln. '+value.reason);
 const target=$(kind==='source'?'source-count':'count');
 if(meaningSignature(kind)===state.signature&&Number(target.value)!==value.recommended_count){target.value=value.recommended_count;target.dispatchEvent(new Event('change',{bubbles:true}));target.dispatchEvent(new Event('input',{bubbles:true}))}
 const apply=add('button','Vorschlag übernehmen: '+value.recommended_count+' Kacheln');apply.type='button';apply.dataset.meaningApply=kind;
 apply.onmousedown=event=>event.preventDefault();
 apply.onclick=()=>{apply.focus({preventScroll:true});if(meaningSignature(kind)!==state.signature){state.status.textContent='Die Textgrundlage wurde geändert. Bitte neu prüfen.';return}const input=$(kind==='source'?'source-count':'count');input.value=value.recommended_count;input.dispatchEvent(new Event('change',{bubbles:true}));input.dispatchEvent(new Event('input',{bubbles:true}));if(kind==='own'){editorPayload.narrative_plan=structuredClone(value);dirty=true;modeHelp()}else updateSourceCountButton();state.status.textContent='Kachelanzahl übernommen. Vorhandene Szenen müssen bei geändertem Umfang neu geplant werden.'};
 add('h4','Mögliche Serie: '+(value.series_count||value.episodes?.length||1)+' Folge'+((value.series_count||value.episodes?.length||1)===1?'':'n')+' mit jeweils 6 Kacheln');
 add('p',value.series_reason||'Die genaue Folgenhandlung wird erst bei der Skripterstellung geplant.');
 const download=add('button','Lehre und Umfang herunterladen');download.type='button';download.onclick=()=>downloadFile(new Blob([JSON.stringify(value,null,2)],{type:'application/json;charset=utf-8'}),'comic-erzaehlplan.json');
 add('small','Umfangsempfehlung zur Vermittlung der Erkenntnis. Noch keine Folgenhandlung oder Bilder erzeugt. Neue Planungen verwenden den aus der Lehre abgeleiteten Umfang.');
}
function mountMeaning(kind,anchor){
 const box=document.createElement('details');box.dataset.meaning=kind;box.open=true;
 const summary=document.createElement('summary');summary.textContent='Pointe, Lehre und passenden Umfang planen';box.append(summary);
 const hint=document.createElement('p');hint.textContent='Zuerst die Lehre prüfen. Daraus folgen 6–18 Kacheln oder eine Serie mit kurzen Folgen; eine freie Kachelvorgabe entfällt.';box.append(hint);
 const button=document.createElement('button');button.type='button';button.textContent='Redaktionelle Auswertung laden';button.dataset.meaningPlan=kind;box.append(button);
 const status=document.createElement('p');status.role='status';box.append(status);
 const output=document.createElement('div');output.hidden=true;box.append(output);anchor.before(box);
 const state={button,status,output,value:null,signature:'',ticket:0};meaningViews.set(kind,state);
 button.onclick=async()=>{
  const input=meaningInput(kind);if(!input.text.trim()){status.textContent='Zuerst eine Textgrundlage eintragen oder eine Quelle wählen.';return}
  if(!Number.isSafeInteger(input.count)||input.count<1){status.textContent='Eine gültige Kachelanzahl eingeben.';return}
  const ticket=++state.ticket,signature=meaningSignature(kind);button.disabled=true;status.textContent='Redaktionelle Auswertung und Umfang laden …';
  try{
   let job=await(await api('/narrative-tasks','POST',input)).json();
   while(['queued','running'].includes(job.status)){
    if(ticket!==state.ticket)return;
    status.textContent=job.status==='queued'?'Erzählplanung wartet …':'Gespeicherte redaktionelle Auswertung wird bereitgestellt …';
    await new Promise(resolve=>setTimeout(resolve,1500));job=await(await api('/jobs/'+job.id)).json();
   }
   if(ticket!==state.ticket)return;
   if(job.status!=='completed')throw Error(job.error||'Erzählplanung fehlgeschlagen.');
   if(meaningSignature(kind)!==signature){status.textContent='Die Textgrundlage wurde zwischenzeitlich geändert. Bitte für den neuen Text erneut planen.';return}
   state.signature=signature;showMeaning(kind,job.narrative_plan);
   if(kind==='own'){editorPayload.narrative_plan=structuredClone(job.narrative_plan);dirty=true;$('definition-state').textContent='Erzählplan noch nicht gespeichert';}
   status.textContent='Lehre und Umfang bereit. Die passende Kachelanzahl wurde übernommen.';
  }catch(e){status.textContent=e.message}finally{if(ticket===state.ticket)button.disabled=false}
 };
}
function restoreMeaning(){const state=meaningViews.get('own');if(!state)return;state.signature=meaningSignature('own');showMeaning('own',editorPayload.narrative_plan||null);state.status.textContent='';}
function installMeaning(){mountMeaning('own',$('dialogue-state'));mountMeaning('source',$('source-create'));installMeaningLibrary();}

let meaningLibraryCompleted=-1;
async function refreshMeaningLibrary(){
 const status=$('meaning-library-status');if(!status)return;
 try{
  const value=await(await api('/narrative-library')).json();
  status.textContent=value.completed+' / '+value.total+' fertig · '+value.pending+' offen · '+value.failed+' fehlgeschlagen. '+(value.deferred?value.deferred+' Quellen für später zurückgestellt. ':'')+(!value.pending&&!value.failed?'Redaktionelle Vorarbeit für alle aktiven Einträge abgeschlossen.':value.editorial_active?'Redaktionelle Auswertung läuft.':value.enabled?(value.pending?'Vorarbeit läuft.':'Neue oder geänderte Geschichten werden automatisch ergänzt.'):'Vorarbeit pausiert.');
  $('meaning-library-progress').max=Math.max(1,value.total);$('meaning-library-progress').value=value.completed;
  $('meaning-library-current').textContent=value.current?'Aktuell: '+value.current.title+(value.enabled?'':' · Pause nach dieser Analyse'):'Aktuell keine Analyse in Arbeit.';
  $('meaning-library-error').textContent=value.last_error?'Letzter Fehler bei „'+value.last_error.title+'“: '+value.last_error.error:'';
  $('meaning-library-pause').hidden=true;
  $('meaning-library-start').hidden=true;
  $('meaning-library-pause').disabled=true;
  $('meaning-library-start').disabled=Boolean(value.editorial_active&&value.pending)||(value.enabled&&!value.failed);
  if(meaningLibraryCompleted!==value.completed){
   const previous=meaningLibraryCompleted;meaningLibraryCompleted=value.completed;
   if(previous>=0&&sourceEntries.length&&!sourceBusy)await loadSources();
   if(definitionId&&!dirty&&!planningJob){
    const doc=await(await api('/stories/'+definitionId)).json();
    if(doc.id===definitionId&&doc.version===definitionVersion&&doc.payload.article===$('article').value&&doc.payload.narrative_plan){editorPayload.narrative_plan=structuredClone(doc.payload.narrative_plan);restoreMeaning()}
   }
  }
 }catch(e){status.textContent=e.message}
}
function installMeaningLibrary(){
 const panel=document.createElement('section');panel.id='meaning-library';
 panel.innerHTML='<h3>Vorarbeit für Geschichten und Quellen</h3><p>Pointe / Lehre, Ursache-Wirkungs-Kette, ideale Kachelanzahl und möglicher Serienplan. Vorhandene Skripte und Comics bleiben erhalten. Neue Vorlagen und Kategorien werden redaktionell über Codex angebunden. Lokale Modelle übernehmen keine Ersatzdeutung.</p><p id="meaning-library-status" role="status">Status wird geladen …</p><progress id="meaning-library-progress" max="1" value="0" aria-label="Fortschritt der Vorarbeit"></progress><p id="meaning-library-current"></p><p id="meaning-library-error" role="status"></p><div class="row"><button type="button" id="meaning-library-start">Starten / Fehler erneut versuchen</button><button type="button" id="meaning-library-pause">Nach aktueller Analyse pausieren</button><button type="button" id="meaning-library-refresh">Fortschritt aktualisieren</button></div>';
 $('workflow-story-selection').before(panel);
 for(const [id,action] of [['meaning-library-start','start'],['meaning-library-pause','pause']])$(id).onclick=async()=>{const button=$(id);button.disabled=true;try{await api('/narrative-library','POST',{action});await refreshMeaningLibrary()}catch(e){$('meaning-library-status').textContent=e.message}finally{button.disabled=false}};
 $('meaning-library-refresh').onclick=()=>refreshMeaningLibrary();
 setInterval(()=>refreshMeaningLibrary(),5000);
}
