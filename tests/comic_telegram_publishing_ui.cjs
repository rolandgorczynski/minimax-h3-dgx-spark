/* Versandoberfläche gegen eine Attrappe; kein externer Aufruf. */
const {chromium}=require('playwright'),assert=require('assert'),path=require('path');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,args:['--no-sandbox']});
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.setContent('<input id="telegram-channel"><button id="telegram-channel-save">Speichern</button><p id="telegram-publishing-state"></p><button id="telegram-publish" disabled>Veröffentlichen</button><a id="telegram-publication-link" hidden>Beitrag</a>');
  await page.evaluate(()=>{
   window.$=id=>document.getElementById(id);window.calls=[];window.shareTicket=1;window.sharePlatform='telegram';window.shareManifest={job_id:'a'.repeat(32),post_version:0};window.saved=0;
   window.saveSharePost=async()=>{saved++;shareManifest.post_version++};
   window.info={configured:true,ready:true,target:{channel:'@test_channel',channel_id:-10012345,bot_username:'comic_bot'},publication:null};
   window.api=async(url,method='GET',data)=>{
    calls.push({url,method,data});
    if(method==='GET')return {json:async()=>info};
    if(method==='POST'){info.publication={status:'sent',url:'https://t.me/test_channel/123'};return {json:async()=>info.publication}}
    throw Error('Unerwarteter Aufruf');
   };
  });
  await page.addScriptTag({path:path.join(__dirname,'../automation/comics/telegram-publish.js')});
  await page.evaluate(async()=>{document.dispatchEvent(new Event('DOMContentLoaded'));await loadTelegramPublishing()});
  assert.equal((await page.evaluate(()=>calls.filter(c=>c.method==='POST'))).length,0);
  assert(await page.locator('#telegram-publish').isEnabled());
  await page.locator('#telegram-publish').click();
  await page.waitForFunction(()=>document.getElementById('telegram-publish').textContent.includes('Bereits'));
  assert.equal(await page.evaluate(()=>saved),1);
  const sent=await page.evaluate(()=>calls.filter(c=>c.method==='POST'));assert.equal(sent.length,1);assert.deepStrictEqual(sent[0].data,{post_version:1,channel_id:-10012345});
  assert(await page.locator('#telegram-publish').isDisabled());assert(await page.locator('#telegram-publication-link').isVisible());
  await page.locator('#telegram-channel').fill('@anderer_kanal');assert(await page.locator('#telegram-publish').isDisabled());
  assert.deepStrictEqual(errors,[]);
  console.log('Telegram-Oberfläche geprüft: nur Klick sendet, gespeicherter Text, Zielkanal, Doppelpost-Schutz und Beitragslink.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
