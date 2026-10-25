let telegramPublishInfo=null,telegramPublishing=false;
function drawTelegramPublishing(info){
 telegramPublishInfo=info;
 $('telegram-channel').value=info.target?.channel||'';
 const record=info.publication;
 $('telegram-publish').disabled=!info.ready||!!record||telegramPublishing;
 $('telegram-publish').textContent=record?.status==='sent'?'Bereits auf Telegram veröffentlicht':'Auf Telegram veröffentlichen';
 $('telegram-publication-link').hidden=!record?.url;
 if(record?.url)$('telegram-publication-link').href=record.url;
 $('telegram-publishing-state').textContent=record?.status==='sent'?'Dieser Comic wurde bereits veröffentlicht.':record?'Ein Versandversuch ist gespeichert. Bitte zuerst den Kanal prüfen.':info.error||(!info.configured?'Bot-Token lokal noch nicht konfiguriert.':!info.target?.channel?'Zielkanal eintragen und prüfen.':'Verbunden: @'+info.target.bot_username+' → '+info.target.channel+'. Der Klick veröffentlicht Bilder und Begleittext direkt.');
}
async function loadTelegramPublishing(){
 telegramPublishInfo=null;$('telegram-publish').disabled=true;
 const manifest=shareManifest,ticket=shareTicket;
 const info=await(await api('/jobs/'+manifest.job_id+'/share/telegram')).json();
 if(ticket===shareTicket&&sharePlatform==='telegram')drawTelegramPublishing(info);
}
document.addEventListener('DOMContentLoaded',()=>{
 $('telegram-channel-save').onclick=async()=>{
  try{
   $('telegram-channel-save').disabled=true;
   const value=await(await api('/telegram-publishing','PUT',{channel:$('telegram-channel').value.trim()})).json();
   drawTelegramPublishing(value);await loadTelegramPublishing();
  }catch(e){$('telegram-publishing-state').textContent=e.message;$('telegram-publish').disabled=true}
  finally{$('telegram-channel-save').disabled=false}
 };
 $('telegram-channel').oninput=()=>{$('telegram-publish').disabled=true;$('telegram-publishing-state').textContent='Geänderten Kanal zuerst speichern und prüfen.'};
 $('telegram-publish').onclick=async()=>{
  if(telegramPublishing||!shareManifest||!telegramPublishInfo?.ready)return;
  telegramPublishing=true;$('telegram-publish').disabled=true;
  const manifest=shareManifest,target=telegramPublishInfo.target,ticket=shareTicket;
  try{
   $('telegram-publishing-state').textContent='Comic wird auf '+target.channel+' veröffentlicht …';
   await saveSharePost();
   if(ticket!==shareTicket||shareManifest?.job_id!==manifest.job_id)throw Error('Ausgabe gewechselt. Es wurde nichts veröffentlicht.');
   const record=await(await api('/jobs/'+manifest.job_id+'/share/telegram','POST',{post_version:shareManifest.post_version,channel_id:target.channel_id})).json();
   if(ticket===shareTicket)drawTelegramPublishing({...telegramPublishInfo,publication:record});
  }catch(e){if(ticket===shareTicket){$('telegram-publishing-state').textContent=e.message;try{const info=await(await api('/jobs/'+manifest.job_id+'/share/telegram')).json();telegramPublishInfo=info;$('telegram-publish').disabled=!info.ready||!!info.publication}catch{}}}
  finally{telegramPublishing=false;if(ticket===shareTicket&&telegramPublishInfo?.ready&&!telegramPublishInfo.publication)$('telegram-publish').disabled=false}
 };
});
