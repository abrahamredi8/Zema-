(() => {
'use strict';const el=id=>document.getElementById(id);let preview;
el('normalizeAudio').onclick=async()=>{
 const file=el('cleanAudioFile').files[0];if(!file){el('cleanAudioStatus').textContent='Choose an audio file first.';return;}
 if(file.size>40*1024*1024){el('cleanAudioStatus').textContent='Use an audio file below 40 MiB.';return;}
 const button=el('normalizeAudio');button.disabled=true;
 try{
  el('cleanAudioStatus').textContent='Processing locally…';
  const context=new(window.AudioContext||window.webkitAudioContext)();let decoded;
  try{decoded=await context.decodeAudioData(await file.arrayBuffer());}finally{await context.close();}
  if(decoded.duration>120)throw Error('Use a clip up to two minutes long.');
  const result=window.ZemaVoiceAudio.normalize(Array.from({length:decoded.numberOfChannels},(_,i)=>decoded.getChannelData(i)),Number(el('volumeTarget').value));
  const blob=new Blob([window.ZemaVoiceAudio.wav(result.channels,decoded.sampleRate)],{type:'audio/wav'});
  if(preview)URL.revokeObjectURL(preview);preview=URL.createObjectURL(blob);
  el('cleanAudioPreview').src=preview;el('cleanAudioPreview').hidden=false;el('cleanAudioDownload').href=preview;el('cleanAudioDownload').hidden=false;
  el('cleanAudioStatus').textContent='Volume adjusted '+(result.gainDb>=0?'+':'')+result.gainDb.toFixed(1)+' dB. Listen before replacing your original recording.';
  window.dispatchEvent(new CustomEvent('zemavoice-result',{detail:{kind:'audio',url:preview,name:'zemavoice-volume-adjusted.wav'}}));
 }catch(error){el('cleanAudioStatus').textContent=error.message;}finally{button.disabled=false;}
};
window.addEventListener('zemavoice-auth-state',event=>{if(event.detail.signedIn)return;if(preview)URL.revokeObjectURL(preview);preview=null;el('cleanAudioFile').value='';el('cleanAudioPreview').removeAttribute('src');el('cleanAudioPreview').hidden=true;el('cleanAudioDownload').hidden=true;});
window.addEventListener('beforeunload',()=>{if(preview)URL.revokeObjectURL(preview);});
})();
