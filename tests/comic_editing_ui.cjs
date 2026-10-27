/* 24 Kacheln: Seiten, gespeicherte Blasen und Einzelbildkorrektur ohne Modellaufruf. */
const fs=require('fs'),path=require('path'),assert=require('assert'),{chromium}=require('playwright');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,args:['--no-sandbox']});try{
 const page=await browser.newPage(),errors=[],calls=[],drafts={};page.on('pageerror',e=>errors.push(String(e)));
 const original='a'.repeat(32),corrected='c'.repeat(32),speaker='b'.repeat(32);
 const png='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6bS8AAAAASUVORK5CYII=';
 let info={job_id:original,version:'v1',title:'Lange Geschichte',story_text:'Eine Geschichte mit 24 Bildern.',characters:[{id:speaker,name:'Ria'}],panels:Array.from({length:24},(_,i)=>({canvas_size:[768,672],story:'Ria an Tür '+i,dialog:'',protected_areas:[],bubbles:[{speaker,text:'Hallo '+i,x:.1,y:.25,w:.4,h:.2,tip_x:.3,tip_y:.7}]}))};
 await page.route('**/*',async route=>{const req=route.request(),p=new URL(req.url()).pathname,method=req.method(),data=req.postData()?JSON.parse(req.postData()):null;calls.push({p,method,data});const reply=v=>route.fulfill({contentType:'application/json',body:JSON.stringify(v)});
  if(p==='/'||p.endsWith('.js'))return route.fulfill({contentType:p==='/'?'text/html':'text/javascript',body:fs.readFileSync(path.join(__dirname,'../automation/comics',p==='/'?'index.html':path.basename(p)))});
  if(p==='/styles')return reply({styles:['Klassischer Comic']});if(p==='/page-templates')return reply({templates:[]});if(p==='/jobs')return reply({jobs:[]});if(p==='/stories')return reply({stories:[]});if(p==='/learning')return reply({analyzed_runs:0,rules:[]});if(p==='/narrative-library')return reply({enabled:false,total:0,completed:0,pending:0});
  if(p.includes('/artifacts/'))return route.fulfill({contentType:'image/png',body:Buffer.from(png,'base64')});
  if(p.endsWith('/lettering/draft')){if(method==='POST')drafts[p]=data;return reply({draft:drafts[p]||null})}
  if(p.endsWith('/lettering/preview'))return reply({valid:true,issues:[],background:png,png,layout:data.layout});
  if(p.endsWith('/correction-plan')){assert.equal(data.correction,'Haare kürzer.');return reply({id:'d'.repeat(32),status:'completed',correction_plan:{story:'Ria hat einen kinnlangen Bob. Alles andere beibehalten.',character_states:{}}})}
  if(p.endsWith('/correct-panel')){assert.equal(data.approved_story,'Ria hat einen kinnlangen Bob. Alles andere beibehalten. Eigene Ergänzung.');assert.equal(data.panel,23);assert.equal(data.panels.length,24);assert.equal(data.correction,'Haare kürzer.');assert.equal(data.panels[23].bubbles[0].text,'Neuer letzter Dialog.');assert(data.panels[0].bubbles[0].x>.1);info={...info,job_id:corrected,version:'v2',panels:info.panels.map((p,i)=>({...p,...data.panels[i]}))};return reply({id:corrected,status:'queued',stage:'queued'})}
  if(p==='/jobs/'+corrected)return reply({id:corrected,status:'needs_review',stage:'finished'});
  if(p.endsWith('/lettering'))return reply(info);
  throw Error('Unerwarteter Testaufruf: '+method+' '+p);
 });
 await page.goto('http://comic.test');await page.waitForFunction(()=>workflowInstalled);
 await page.evaluate(({id})=>{selected=id;list=async()=>{};}, {id:original});
 const job={id:original,artifacts:['comic.png','pages/01.png','pages/02.png','pages/03.png','pages/04.png'].map(name=>({name}))};
 await page.evaluate(job=>loadComicPages(job),job);
 await page.click('[data-workflow-step="edit"]');assert.equal(await page.locator('#comic-page-select option').count(),4);
 await page.click('#comic-page-next');assert.equal(await page.locator('#comic-page-select').inputValue(),'1');
 await page.selectOption('#comic-page-select','3');assert(await page.locator('#comic-page-next').isDisabled());assert((await page.locator('#comic').getAttribute('alt')).includes('4 von 4'));
 await page.evaluate(()=>document.getElementById('lettering-edit').onclick());await page.waitForFunction(()=>positionData&&positionExact);
 await page.locator('#position-canvas rect[aria-label="Sprechblase 1 verschieben"]').dispatchEvent('keydown',{key:'ArrowRight'});
 await page.selectOption('#position-panel','12');await page.click('#position-next');assert.equal(await page.locator('#position-panel').inputValue(),'13');
 await page.selectOption('#position-panel','23');assert(await page.locator('#position-next').isDisabled());
 await page.fill('#position-text','Neuer letzter Dialog.');await page.fill('#position-correction-text','Haare kürzer.');await page.click('#position-draft-save');await page.waitForFunction(()=>!positionDirty);
 await page.click('#position-close');await page.evaluate(()=>document.getElementById('lettering-edit').onclick());await page.waitForFunction(()=>positionData&&positionIndex===23);
 assert.equal(await page.locator('#position-text').inputValue(),'Neuer letzter Dialog.');assert.equal(await page.locator('#position-correction-text').inputValue(),'Haare kürzer.');
 assert(await page.locator('#position-correction-run').isDisabled());
 await page.click('#position-correction-refine');await page.waitForFunction(()=>!positionBusy&&positionPlans[23]);
 assert.equal(calls.filter(c=>c.p.endsWith('/correct-panel')).length,0);
 assert.equal(await page.locator('#position-source-scene').inputValue(),'Ria hat einen kinnlangen Bob. Alles andere beibehalten.');
 await page.fill('#position-source-scene','Ria hat einen kinnlangen Bob. Alles andere beibehalten. Eigene Ergänzung.');
 await page.click('#position-draft-save');await page.waitForFunction(()=>!positionDirty);await page.click('#position-close');await page.evaluate(()=>document.getElementById('lettering-edit').onclick());await page.waitForFunction(()=>positionData&&positionIndex===23);
 assert((await page.locator('#position-source-scene').inputValue()).endsWith('Eigene Ergänzung.'));
 await page.click('#position-correction-run');await page.waitForFunction(id=>positionData?.job_id===id&&!positionBusy,corrected);
 assert.equal(await page.locator('#position-panel').inputValue(),'23');assert.equal(await page.locator('#position-text').inputValue(),'Neuer letzter Dialog.');assert.equal(await page.locator('#position-correction-text').inputValue(),'');
 assert.equal(calls.filter(c=>c.p.endsWith('/correct-panel')).length,1);assert.equal(drafts['/jobs/'+corrected+'/lettering/draft'].panels.length,24);assert.deepStrictEqual(errors,[]);
 console.log('24 Kacheln und vier Seiten navigierbar; Stand nach Schließen wiederhergestellt; einzelne Bildkorrektur übernimmt alle Blasen und speichert neuen Stand. Keine echten Modellaufrufe.');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
