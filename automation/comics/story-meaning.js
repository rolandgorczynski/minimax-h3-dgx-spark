/* Redaktionelle Auswertung anzeigen und als eigene Vorgabe bearbeiten; Neuplanung erst auf Klick. */
const meaningViews=new Map();
function meaningInput(kind){return kind==='source'?{text:$('source-text').value,instructions:$('source-instructions').value,count:Number($('source-count').value),identity:sourceSelected}:{text:$('article').value,instructions:'',count:Number($('count').value),identity:definitionId}}
function meaningSignature(kind){const {count,...value}=meaningInput(kind);return JSON.stringify(value)}
function showMeaning(kind,value){
 const state=meaningViews.get(kind);if(!state)return;
 state.value=value;state.output.replaceChildren();state.output.hidden=!value;
 if(!value){state.status.textContent='Für diese Textgrundlage ist noch keine redaktionelle Auswertung hinterlegt. Zuerst redaktionell vorbereiten lassen.';return}
 const add=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;state.output.append(el);return el};
 const field=(key,title,limit)=>{const label=add('label',title),input=document.createElement('textarea');input.value=value[key]||'';input.maxLength=limit;input.dataset.meaningField=key;label.append(input);input.addEventListener('input',()=>{value[key]=input.value;changed()})};
 function changed(){value.user_edited=true;state.signature=meaningSignature(kind);if(kind==='own'){editorPayload.narrative_plan=structuredClone(value);editorPayload.script_needs_replan=true;dirty=true;rememberEditedStory();$('definition-state').textContent='Auswertung geändert · Skript neu erstellen';modeHelp()}else{$('source-adopt').disabled=true;sourceMessage('Auswertung geändert. Skript erneut erstellen, bevor du es als Geschichte übernimmst.')}state.status.textContent='Deine Auswertung wird bei „Skript neu erstellen“ übernommen. Bisherige Szenen bleiben bis dahin erhalten.'}
 field('central_question','Menschliche Grundfrage',600);
 const label=add('label','Art der Auswertung'),type=document.createElement('select');for(const text of ['Lehre','Erkenntnis','Offene Frage'])type.add(new Option(text,text));type.value=value.meaning_type||'Lehre';label.append(type);type.onchange=()=>{value.meaning_type=type.value;changed()};
 field('core','Lehre / Kernaussage',1200);
 field('ending','Schluss und Schlusswirkung',1200);
 const evidence=add('details',''),summary=document.createElement('summary');summary.textContent='Begründung und Handlungskette bearbeiten';evidence.append(summary);
 for(const [index,item] of (value.evidence||[]).entries()){for(const [key,title] of [['event','Beleg aus der Handlung'],['meaning','Bedeutung dieses Belegs']]){const label=document.createElement('label');label.textContent=title;const input=document.createElement('textarea');input.maxLength=600;input.value=item[key];label.append(input);evidence.append(label);input.oninput=()=>{value.evidence[index][key]=input.value;changed()}}}
 const chain=document.createElement('label');chain.textContent='Ursache-Wirkungs-Kette · ein Schritt je Zeile';const input=document.createElement('textarea');input.value=(value.causal_chain||[]).join('\n');input.maxLength=9600;chain.append(input);evidence.append(chain);input.oninput=()=>{value.causal_chain=input.value.split('\n').map(t=>t.trim()).filter(Boolean);changed()};
 add('p','Redaktionelle Empfehlung: '+value.recommended_count+' Kacheln. '+value.reason+' Die gewählte Kachelzahl steht neben der Geschichtenauswahl.');
 if(kind==='source'&&meaningSignature(kind)===state.signature&&!value.user_edited){$('source-count').value=value.recommended_count;updateSourceCountButton()}
 add('small',value.user_edited?'Von dir bearbeitete Auswertung. Sie bleibt unabhängig von der ursprünglichen Quellenanalyse gespeichert.':'Redaktionelle Auswertung. Wird bei der Auswahl automatisch angezeigt; keine erneute Analyse gestartet.');
}
function mountMeaning(kind,anchor){
 const box=document.createElement('details');box.dataset.meaning=kind;box.open=true;
 const summary=document.createElement('summary');summary.textContent='Redaktionelle Auswertung · Lehre und Erzählkern';box.append(summary);
 const hint=document.createElement('p');hint.textContent='Grundfrage, Lehre und Schluss prüfen und bei Bedarf bearbeiten. Danach das vollständige Skript neu erstellen. Es werden keine Bilder erzeugt.';box.append(hint);
 const status=document.createElement('p');status.role='status';box.append(status);
 const output=document.createElement('div');output.hidden=true;box.append(output);anchor.before(box);
 const state={status,output,value:null,signature:'',ticket:0};meaningViews.set(kind,state);
}
function restoreMeaning(){const state=meaningViews.get('own');if(!state)return;state.signature=meaningSignature('own');showMeaning('own',editorPayload.narrative_plan||null);if(state.value)state.status.textContent='';}
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
 panel.innerHTML='<h3>Vorarbeit für Geschichten und Quellen</h3><p>Pointe / Lehre, Ursache-Wirkungs-Kette, ideale Kachelanzahl und möglicher Serienplan. Vorhandene Skripte und Comics bleiben erhalten. Neue Vorlagen und Kategorien werden redaktionell über Codex angebunden. Lokale Modelle übernehmen keine Ersatzdeutung.</p><p id="meaning-library-status" role="status">Status wird geladen …</p><progress id="meaning-library-progress" max="1" value="0" aria-label="Fortschritt der Vorarbeit"></progress><p id="meaning-library-current"></p><p id="meaning-library-error" role="status"></p><div class="row"><button type="button" id="meaning-library-start">Starten / Fehler erneut versuchen</button><button type="button" id="meaning-library-pause">Nach aktueller Analyse pausieren</button></div>';
 $('workflow-story-selection').before(panel);
 for(const [id,action] of [['meaning-library-start','start'],['meaning-library-pause','pause']])$(id).onclick=async()=>{const button=$(id);button.disabled=true;try{await api('/narrative-library','POST',{action});await refreshMeaningLibrary()}catch(e){$('meaning-library-status').textContent=e.message}finally{button.disabled=false}};
 setInterval(()=>refreshMeaningLibrary(),5000);
}
