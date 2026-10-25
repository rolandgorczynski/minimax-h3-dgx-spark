/* Figuren tauschen im echten Browser mit API-Attrappen; keine Modelle/Generierung. */
const fs=require('fs'),path=require('path'),assert=require('assert'),{chromium}=require('playwright');
const root=path.join(__dirname,'..'),web=path.join(root,'automation/comics');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[],calls=[];
  page.on('pageerror',e=>errors.push(String(e)));
  const target='a'.repeat(32),other='b'.repeat(32),lib='c'.repeat(32),sid='d'.repeat(32),broken='e'.repeat(32),conflict='f'.repeat(32);
  const png='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6bS8AAAAASUVORK5CYII=';
  const profile={id:lib,name:'Nora',description:'Kurze dunkle Haare, Sommersprossen.',outfit:'Grüne Jacke.',backstory:'Wuchs am Hafen auf.',personality:'Mutig.',motivation:'Ihre Schwester finden.',alignment:'chaotic_good',aliases:['Die Sucherin'],references:['portrait.png'],version:3};
  let library=[profile,{...structuredClone(profile),id:broken,name:'Mira',references:['broken.png']},{...structuredClone(profile),id:conflict,name:'Arik',aliases:[],references:[]}];
  const original={id:sid,version:1,name:'Die Geisterbrücke',mode:'editorial',payload:{title:'Die Geisterbrücke',article:'Ria begegnet Arik.',planned_article:'Ria begegnet Arik.',planned_count:2,panel_count:2,style:'Klassischer Comic',visual_style_pending:false,seed:1984,
   characters:[{id:target,name:'Ria',description:'Lange blonde Haare.',outfit:'Blauer Mantel.',aliases:['Die Finderin'],references:[]},{id:other,name:'Arik',description:'Älterer Mann.',outfit:'Mantel.',aliases:[],references:[]}],
   library_ids:[target],narrator_badge:true,narrator_character_id:target,
   reference_overrides:{[target]:['altes-bild'],[other]:['anderes-bild']},outfits:{[target]:'Alte Kleidung',[other]:'Andere Kleidung'},
   scenes:[{story:'Ria steht neben Arik auf der Brücke.',dialog:'Ein Geist wartet.',characters:[target,other],bubbles:[{speaker:target,text:'Wer bist du?',x:.1,y:.2,w:.3,h:.2,source_quote_id:'q001'}],character_states:{[target]:'Steht auf der Brücke.',[other]:'Steht am Tor.'},continuity_state:{[target]:{movement:'zu Fuß',location:'Brücke'}}},
   {story:'Ria geht zum Tor.',dialog:'',characters:[target],bubbles:[{speaker:'Ria',text:'Komm mit!',source_quote_id:'q002'}]}]}};
  let story=structuredClone(original);
  const catalog=JSON.parse(fs.readFileSync(path.join(root,'extensions/dgx-comics/style_catalog.json')));
  await page.route('**/*',async route=>{
   const req=route.request(),url=new URL(req.url()),p=url.pathname,method=req.method(),data=req.postData()?JSON.parse(req.postData()):null;
   calls.push({path:p,method,data});const reply=value=>route.fulfill({contentType:'application/json',body:JSON.stringify(value)});
   if(p==='/'||p.endsWith('.js'))return route.fulfill({contentType:p==='/'?'text/html':'text/javascript',body:fs.readFileSync(path.join(web,p==='/'?'index.html':path.basename(p)))});
   if(p==='/styles')return reply({styles:catalog.map(s=>s.name),catalog:catalog.map(s=>({...s,preview:'/preview.webp'}))});
   if(p==='/page-templates')return reply({templates:[{id:'standard',name:'Standard',category:'Raster',count:2,aspect_ratio:1,slots:[[0,0,1,.5],[0,.5,1,.5]]}]});
   if(p==='/jobs')return reply({jobs:[]});if(p==='/learning')return reply({analyzed_runs:0,rules:[]});
   if(p==='/stories'&&method==='GET')return reply({stories:[{id:sid,name:story.name,mode:story.mode,version:story.version}]});
   if(p==='/stories/'+sid&&method==='GET')return reply(story);
   if(p==='/stories/'+sid&&method==='PATCH'){story={...data,id:sid,version:story.version+1};return reply(story)}
   if(p==='/characters'&&method==='GET')return reply({characters:library,alignments:[]});
   if(p==='/characters'&&method==='POST'){const saved={...data,version:data.version+1};library=library.map(c=>c.id===data.id?saved:c);return reply(saved)}
   if(p==='/characters/'+lib+'/references/portrait.png')return route.fulfill({contentType:'image/png',body:Buffer.from(png,'base64')});
   if(p==='/characters/'+broken+'/references/broken.png')return route.fulfill({status:404,contentType:'application/json',body:'{"error":"Referenzbild fehlt"}'});
   throw Error('Unerwarteter Testaufruf: '+method+' '+p);
  });
  await page.goto('http://comic.test/');await page.waitForFunction(()=>workflowInstalled&&definitionId);
  await page.click('[data-workflow-step="render"]');
  const card=page.locator('#story-characters [data-character-id="'+target+'"]');
  await card.locator('summary').click();await card.getByRole('button',{name:'Bibliothek laden',exact:true}).click();
  await page.waitForFunction(()=>characterLibraryLoaded);await card.locator('summary').click();
  const select=page.locator('[data-character-replacement="'+target+'"]'),apply=page.locator('[data-character-replacement-apply="'+target+'"]');
  assert(await apply.isDisabled());
  const gallery=page.locator('[data-character-replacement-gallery="'+target+'"]');
  assert.equal(await gallery.locator('[data-library-choice]').count(),3);
  const tile=gallery.locator('[data-library-choice="'+lib+'"]');
  await tile.scrollIntoViewIfNeeded();
  await page.waitForFunction(({target,lib})=>document.querySelector('[data-character-replacement-gallery="'+target+'"] [data-library-choice="'+lib+'"] img')?.naturalWidth>0,{target,lib},{timeout:10000});
  const initial=await page.evaluate(()=>JSON.stringify(editorPayload));
  await tile.click();assert.equal(await select.inputValue(),lib);
  assert.equal(await tile.getAttribute('aria-pressed'),'true');
  assert.equal(await page.evaluate(()=>JSON.stringify(editorPayload)),initial);
  assert(await gallery.locator('[data-library-choice="'+conflict+'"] .character-library-choice-placeholder').isVisible());
  const preview=page.locator('[data-character-replacement-preview="'+target+'"]');
  await preview.waitFor({state:'visible'});await preview.click();
  assert(await page.locator('#character-picture-dialog').isVisible());
  await page.click('#character-picture-close');
  await page.setViewportSize({width:390,height:844});
  const bounds=await gallery.boundingBox(),cardBounds=await card.boundingBox();
  assert(bounds.width<=cardBounds.width);await page.setViewportSize({width:1440,height:1100});
  await card.screenshot({path:'/tmp/comic-character-preview-picker.png'});
  const before=await page.evaluate(()=>JSON.stringify(editorPayload));
  page.once('dialog',d=>d.dismiss());await apply.click();assert.equal(await page.evaluate(()=>JSON.stringify(editorPayload)),before);
  // Eine fehlende Referenz darf das alte Profil und dessen Zuordnungen nicht verändern.
  await select.selectOption(broken);page.once('dialog',d=>d.accept());await apply.click();
  await page.waitForFunction(id=>document.querySelector('[data-character-replacement-status="'+id+'"]').textContent.includes('Referenzbild fehlt'),target);
  assert.equal(await page.evaluate(()=>JSON.stringify(editorPayload)),before);
  // Namenskonflikte ebenfalls ohne Teiländerung zurückweisen.
  await select.selectOption(conflict);page.once('dialog',d=>d.accept());await apply.click();
  await page.waitForFunction(id=>document.querySelector('[data-character-replacement-status="'+id+'"]').textContent.includes('bereits'),target);
  assert.equal(await page.evaluate(()=>JSON.stringify(editorPayload)),before);
  // Ungespeicherte Szeneneingaben überleben den Tausch.
  await page.evaluate(()=>{document.querySelector('.scene-card [data-key="dialog"]').value='Noch nicht gespeicherter Erzählertext.'});
  await select.selectOption(lib);page.once('dialog',d=>d.accept());await apply.click();
  await page.waitForFunction(()=>editorPayload.characters[0].name==='Nora');
  const result=await page.evaluate(()=>structuredClone(editorPayload)),copy=result.characters[0];
  assert.equal(copy.id,target);assert.equal(copy.library_source_id,lib);assert.equal(copy.backstory,profile.backstory);assert.equal(copy.alignment,profile.alignment);
  assert.deepStrictEqual(copy.references,[]);assert.deepStrictEqual(copy.inline_references,[png]);
  assert(copy.aliases.includes('Ria'));assert(copy.aliases.includes('Die Finderin'));assert(copy.aliases.includes('Die Sucherin'));
  assert.equal(result.article,original.payload.article);assert.equal(result.planned_article,original.payload.planned_article);
  assert.deepStrictEqual(result.scenes[0].characters,[target,other]);assert.equal(result.scenes[0].bubbles[0].speaker,target);
  assert.equal(result.scenes[0].bubbles[0].text,'Wer bist du?');assert.equal(result.scenes[0].bubbles[0].source_quote_id,'q001');
  assert.equal(result.scenes[1].bubbles[0].speaker,target);assert.equal(result.scenes[1].bubbles[0].text,'Komm mit!');
  assert.equal(result.scenes[0].dialog,'Noch nicht gespeicherter Erzählertext.');
  assert.deepStrictEqual(result.scenes[0].character_states,original.payload.scenes[0].character_states);
  assert.deepStrictEqual(result.scenes[0].continuity_state,original.payload.scenes[0].continuity_state);
  assert.equal(result.narrator_character_id,target);assert.equal(result.narrator_badge,true);
  assert(!result.reference_overrides[target]);assert(!result.outfits[target]);assert.deepStrictEqual(result.reference_overrides[other],['anderes-bild']);
  assert.deepStrictEqual(result.library_ids,[]);assert.equal(result.characters.length,2);
  assert.deepStrictEqual(result.characters[1],original.payload.characters[1]);
  assert.deepStrictEqual(await page.evaluate(id=>characterLibrary.find(c=>c.id===id),lib),profile);
  assert(await page.evaluate(()=>dirty));assert(!calls.some(c=>c.method==='POST'||c.method==='PATCH'));
  await page.click('#render-save');await page.waitForFunction(()=>!dirty);
  const saved=calls.filter(c=>c.method==='PATCH').at(-1);assert.equal(saved.data.payload.characters[0].id,target);assert.equal(saved.data.payload.characters[0].library_source_id,lib);
  await page.evaluate(doc=>fillDefinition(doc),story);assert.equal(await page.evaluate(()=>editorPayload.characters[0].name),'Nora');
  // Explizites Zurückspeichern in die Bibliothek verwendet deren ID, keine neue Dublette.
  await card.locator('summary').click();await card.getByRole('button',{name:'In Bibliothek speichern',exact:true}).click();
  await page.waitForFunction(()=>characterLibrary.find(c=>c.name==='Nora')?.version===4);
  const write=calls.find(c=>c.path==='/characters'&&c.method==='POST');assert.equal(write.data.id,lib);assert.equal(write.data.version,3);
  assert(!calls.some(c=>c.path.includes('/generate')||c.path.includes('/regenerate')||c.path.includes('/plan')));
  // Die maximale Figurenanzahl hindert einen Tausch nicht: Es wird nichts hinzugefügt.
  const full=structuredClone(original);full.payload.library_ids=[];
  for(let i=2;i<8;i++)full.payload.characters.push({id:String(i).repeat(32),name:'Nebenfigur '+i,description:'Person.',outfit:'Mantel.',aliases:[],references:[]});
  await page.evaluate(doc=>fillDefinition(doc),full);await card.locator('summary').click();
  await select.selectOption(lib);page.once('dialog',d=>d.accept());await apply.click();await page.waitForFunction(()=>editorPayload.characters[0].name==='Nora');
  assert.equal(await page.evaluate(()=>editorPayload.characters.length),8);
  assert.deepStrictEqual(errors,[]);
  await page.screenshot({path:'/tmp/comic-character-replacement.png',fullPage:true});
  console.log('Bibliotheksfigur ersetzt erkanntes Profil: private Bilder, feste Story-ID, Sprecher und Zustände erhalten; Abbruch/Fehler atomar; Speichern und Bibliotheks-ID geprüft. Keine Generierung.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
