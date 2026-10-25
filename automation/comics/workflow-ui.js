/* Vier getrennte Arbeitsschritte; Navigation verändert keine gespeicherten Daten. */
let workflowInstalled=false,workflowStep='script',workflowOutput=null;
function showWorkflowStep(step){
 if(!['script','render','edit','publish'].includes(step))return;
 workflowStep=step;
 for(const value of ['script','render','edit','publish'])$('workflow-'+value).hidden=value!==step;
 for(const button of document.querySelectorAll('[data-workflow-step]'))button.setAttribute('aria-current',button.dataset.workflowStep===step?'step':'false');
 updateWorkflowState();$('workflow-navigation').scrollIntoView({behavior:'smooth',block:'start'});
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
 const selector=$('render-story-list');selector.replaceChildren(new Option('Skript auswählen',''),...definitions.map(doc=>new Option(doc.name,doc.id)));selector.value=definitionId;
 const ready=$('editor-mode').value==='editorial'&&!needsPlan()&&!planningJob;
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
 if(job?.story_id===definitionId&&(dirty||job.story_version!==definitionVersion))area.textContent+=' Skript oder Gestaltung wurden inzwischen bearbeitet. Diese Ausgabe zeigt ihren gespeicherten Stand; neuere Änderungen erfordern eine neue Comic-Ausgabe.';
 $('edit-to-publish').disabled=!job||!job.artifacts?.some(a=>a.name==='comic.png');
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
 $('workflow-render').addEventListener('input',event=>{if(['render-story-list','page-template-category'].includes(event.target.id))return;dirty=true;$('definition-state').textContent='Ungespeicherte Änderungen';modeHelp()});
 $('style').addEventListener('change',()=>{editorPayload.visual_style_pending=!$('style').value;dirty=true;modeHelp()});
 $('new').addEventListener('click',()=>{if(!definitionId&&!dirty)showWorkflowInput('own')});
 $('story-list').addEventListener('change',()=>showWorkflowInput('own'));
 workflowInstalled=true;showWorkflowInput('own');
}
document.addEventListener('DOMContentLoaded',installWorkflowUI);
