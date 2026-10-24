/* Browserprüfung ohne Server oder Modellaufruf. NODE_PATH muss Playwright enthalten. */
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}:{}),args:['--no-sandbox']});
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(String(e)));
  const html=fs.readFileSync(path.join(__dirname,'../automation/comics/index.html'),'utf8');
  const section=html.slice(html.indexOf('<section><details id="source-generator"'),html.indexOf('</details></section>')+20);
  await page.setContent('<select id="style"><option>Ligne claire</option></select>'+section);
  const sources=JSON.parse(require('child_process').execFileSync('python3',['-c',`
import ast,json,pathlib,sys
sys.path.insert(0,'automation/comics')
from source_categories import decorate
nodes=ast.parse(pathlib.Path('automation/comics/source_generator.py').read_text()).body
entries=next(ast.literal_eval(n.value) for n in nodes if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='BUILTINS' for t in n.targets))
for p in pathlib.Path('examples/comics/sources').glob('*.json'):entries+=json.loads(p.read_text())['sources']
print(json.dumps([decorate(x) for x in entries],ensure_ascii=False))
`],{cwd:path.join(__dirname,'..'),maxBuffer:16*1024*1024,encoding:'utf8'}));
  await page.evaluate(entries=>{
   window.$=id=>document.getElementById(id);window.testEntries=entries;window.testRequests=[];
   window.api=async(url,method='GET',value)=>{
    window.testRequests.push({url,method});
    if(url==='/styles')return {json:async()=>({styles:['Ligne claire']})};
    if(url==='/sources'&&method==='GET')return {json:async()=>({sources:window.testEntries})};
    if(url==='/sources'&&method==='POST'){
     const old=window.testEntries.find(s=>s.id===value.id);
     const result={...value,id:value.id||'neue-probe',category:value.category||'Eigene Vorlagen',collection:old?.collection||'Eigene Quellen'};
     window.testEntries=window.testEntries.filter(s=>s.id!==result.id).concat([result]);return {json:async()=>result};
    }
    throw Error('Unerwarteter Aufruf: '+url);
   };
  },sources);
  await page.addScriptTag({path:path.join(__dirname,'../automation/comics/source-generator.js')});
  await page.evaluate(async()=>{installSourceGenerator();await loadSources();document.getElementById('source-generator').open=true});
  assert((await page.locator('#source-result-count').textContent()).includes('1000 passende'));
  const initial=await page.locator('#source-select').inputValue();
  await page.locator('#source-data').evaluate(el=>el.open=true);
  await page.locator('#source-text').fill('Meine ungespeicherte Bearbeitung bleibt erhalten.');
  await page.selectOption('#source-category-filter','Geister und Spuk');
  await page.locator('#source-search').fill('kopflose');
  assert.strictEqual(await page.locator('#source-select').inputValue(),initial);
  assert.strictEqual(await page.locator('#source-text').inputValue(),'Meine ungespeicherte Bearbeitung bleibt erhalten.');
  assert((await page.locator('#source-result-count').textContent()).includes('außerhalb')===false);
  assert((await page.locator('#source-result-count').textContent()).includes('zusätzlich ausgewählt'));
  const found=await page.locator('#source-select optgroup').allTextContents();assert(found.join(' ').includes('Der kopflose Reiter'));
  await page.locator('#source-search').fill('xyz-keine-vorlage');
  assert((await page.locator('#source-result-count').textContent()).startsWith('0 passende'));
  await page.click('#source-reload');
  await page.waitForFunction(()=>testRequests.filter(x=>x.url==='/sources').length>=2);
  assert.strictEqual(await page.locator('#source-text').inputValue(),'Meine ungespeicherte Bearbeitung bleibt erhalten.');
  await page.locator('#source-search').fill('');await page.selectOption('#source-category-filter','');
  await page.selectOption('#source-collection-filter','Andersen – Märchen');
  assert((await page.locator('#source-result-count').textContent()).startsWith('5 passende'));
  await page.click('#source-new');await page.locator('#source-title').fill('Meine Probe');
  await page.locator('#source-text').fill('Eine eigene Vorlage.');await page.locator('#source-category').fill('Meine Sammlung');
  await page.click('#source-save');await page.waitForFunction(()=>document.getElementById('source-status').textContent.includes('Quelle gespeichert'));
  assert.strictEqual(await page.locator('#source-category').inputValue(),'Meine Sammlung');
  assert.strictEqual(await page.locator('#source-select').inputValue(),'neue-probe');
  assert((await page.locator('#source-category-filter').textContent()).includes('Meine Sammlung (1)'));
  assert.strictEqual(await page.evaluate(()=>sourceDraftChanged()),false);
  assert(!(await page.evaluate(()=>testRequests)).some(x=>x.url.includes('source-tasks')));
  assert.deepStrictEqual(errors,[]);
  console.log('Browserprüfung bestanden: 1.000 Quellen, Themen, Sammlungen, Suche, Entwurfsschutz, Speichern; kein Generierungslauf.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
