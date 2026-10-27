/* Ausgabenverlauf und Warnungsnavigation; nur API-Attrappen, keine Erzeugung. */
const fs=require('fs'),path=require('path'),assert=require('assert'),{chromium}=require('playwright');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,args:['--no-sandbox']});try{
 const page=await browser.newPage(),errors=[],calls=[];page.on('pageerror',e=>errors.push(String(e)));
 const story='1'.repeat(32),other='2'.repeat(32),a='a'.repeat(32),b='b'.repeat(32),c='c'.repeat(32),d='d'.repeat(32),e='e'.repeat(32),old='f'.repeat(32);
 const make=(id,date,extra={})=>({id,story_id:story,story_title:'Gleicher Titel',status:'needs_review',stage:'finished',artifacts:[],created_at:'2026-10-27T10:0'+date+':00Z',...extra});
 const originals=[make(c,5,{parent_job:b,panel_correction_mode:true,corrected_panel:8}),make(e,4),make(d,3,{story_id:other}),make(b,2,{parent_job:a,lettering_mode:true}),make(a,1)];
 await page.route('**/*',async route=>{const req=route.request(),p=new URL(req.url()).pathname;calls.push([req.method(),p]);const reply=v=>route.fulfill({contentType:'application/json',body:JSON.stringify(v)});
  if(p==='/'||p.endsWith('.js'))return route.fulfill({contentType:p==='/'?'text/html':'text/javascript',body:fs.readFileSync(path.join(__dirname,'../automation/comics',p==='/'?'index.html':path.basename(p)))});
  if(p==='/styles')return reply({styles:['Klassischer Comic']});if(p==='/page-templates')return reply({templates:[]});if(p==='/jobs')return reply({jobs:[]});if(p==='/stories')return reply({stories:[]});if(p==='/learning')return reply({analyzed_runs:0,rules:[]});if(p==='/narrative-library')return reply({enabled:false,total:0,completed:0,pending:0});
  if(p==='/jobs/'+old)return reply(make(old,0));
  throw Error('Unerwartete Anfrage: '+p);
 });
 await page.goto('http://comic.test');await page.waitForFunction(()=>workflowInstalled);
 await page.evaluate(({data,id})=>{jobs=data;selected=id;show=async()=>updateOutputHistory(jobs.find(j=>j.id===selected));renderOutputSelection();updateOutputHistory(jobs.find(j=>j.id===selected))},{data:originals,id:c});
 assert.equal(await page.locator('#jobs optgroup').count(),2);assert.equal(await page.locator('#jobs option').count(),2);
 await page.evaluate(()=>document.getElementById('output-show-history').click());assert.equal(await page.locator('#jobs option').count(),5);await page.evaluate(()=>document.getElementById('output-show-history').click());
 await page.evaluate(()=>document.getElementById('output-prev').click());await page.waitForFunction(id=>selected===id,b);assert((await page.locator('#output-current').textContent()).includes('Ältere Fassung'));assert.equal(await page.locator('#jobs option').count(),3);
 await page.evaluate(()=>document.getElementById('output-original').click());await page.waitForFunction(id=>selected===id,a);assert(await page.locator('#output-original').isDisabled());
 await page.evaluate(()=>document.getElementById('output-latest').click());await page.waitForFunction(id=>selected===id,c);
 await page.evaluate(({root,old})=>{jobs.find(j=>j.id===root).parent_job=old},{root:a,old});await page.evaluate(()=>document.getElementById('output-original').click());await page.waitForFunction(id=>selected===id,old);assert(calls.some(x=>x[1]==='/jobs/'+old));
 await page.evaluate(({id})=>{selected=id;document.getElementById('lettering-edit').onclick=async()=>{positionData={job_id:selected,panels:Array.from({length:16},()=>({}))}};showPositionPanel=async index=>{window.issueIndex=index};drawOutputWarnings({...jobs.find(j=>j.id===id),lettering_unresolved:true,lettering_warnings:['ENTWURF: Texte prüfen.','Kachel 1: Sprechblase verdeckt den Erzählerkasten.','Kachel 5: Sprechblase verdeckt die Kachelnummer.']})},{id:c});
 assert.equal(await page.locator('#lettering-issues li').count(),2);await page.evaluate(()=>document.querySelector('[data-issue-panel="5"]').click());await page.waitForFunction(()=>window.issueIndex===4);
 assert.equal(await page.locator('#panel-correction').count(),0);assert.equal(await page.locator('#experiment-back').count(),0);
 assert.equal(await page.locator('#lettering-edit').textContent(),'Bilder und Texte bearbeiten');assert.equal(await page.locator('#x-share').textContent(),'Für X vorbereiten');assert.equal(await page.locator('#substack-share').textContent(),'Für Substack vorbereiten');
 assert((await page.locator('#position-apply').textContent()).includes('Neue fertige Ausgabe'));assert((await page.locator('#position-correction-run').textContent()).includes('Ganze Kachel'));
 assert.deepStrictEqual(errors,[]);assert(!calls.some(x=>x[0]!=='GET'));console.log('Gruppierter Verlauf, ältere Fassung, vorige/Basis/neueste Ausgabe, Nachladen alter Basis und direkter Sprung zu Kachel 5 geprüft. Keine schreibenden API-Aufrufe.');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
