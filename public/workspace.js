(() => {
'use strict';
const el=id=>document.getElementById(id), profiles=window.ZemaVoiceProfiles;
let available=[], signedIn=window.ZemaVoiceSignedIn===true;
const exports=new Map();
function sendKey(){const frame=el('videoTool');if(frame.contentWindow&&frame.getAttribute('src'))frame.contentWindow.postMessage({type:'zemavoice-connection',key:el('key').value},location.origin);}
function open(mode){switchTab(mode);if(mode==='video'||mode==='dialogue'){const frame=el(mode==='video'?'videoTool':'dialogueTool');if(!frame.getAttribute('src'))frame.src=frame.dataset.src;}document.querySelectorAll('[data-mode][role=tab]').forEach(tab=>tab.tabIndex=tab.dataset.mode===mode?0:-1);}
const tabs=[...document.querySelectorAll('[data-mode][role=tab]')];
tabs.forEach((tab,index)=>{tab.onclick=()=>open(tab.dataset.mode);tab.onkeydown=event=>{let next;if(event.key==='ArrowRight')next=(index+1)%tabs.length;else if(event.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=tabs.length-1;else return;event.preventDefault();tabs[next].focus();open(tabs[next].dataset.mode);};});
function library(){
 const area=el('voiceLibrary');area.replaceChildren();
 const query=el('voiceSearch').value.toLowerCase(), filter=el('voiceFilter').value;
 const entries=[...available.map(v=>({...v,available:true})),...profiles];
 for(const voice of entries){
  if(filter==='available'&&!voice.available)continue;
  if(['Male','Female'].includes(filter)&&voice.gender!==filter)continue;
  if(!(voice.name+' '+(voice.description||'')).toLowerCase().includes(query))continue;
  const card=document.createElement('article');card.className='voice-card';
  const badge=document.createElement('span');badge.className='badge';badge.textContent=voice.available?'Provider voice':(voice.gender+' · Planned');
  const title=document.createElement('h3');title.textContent=voice.name;
  const description=document.createElement('p');description.textContent=voice.description||'Available from your connected speech provider.';
  const button=document.createElement('button');button.type='button';button.disabled=!voice.available;button.textContent=voice.available?'Use this voice':'Audio not connected';
  if(voice.available)button.onclick=()=>{el('voice').value=voice.id;open('voice');};
  card.append(badge,title,description,button);area.append(card);
 }
 if(!area.children.length){const empty=document.createElement('p');empty.textContent='No voices match this filter.';area.append(empty);}
 el('libraryStatus').textContent='20 planned voice profiles · '+available.length+' provider voices loaded. Planned profiles are voice briefs, not additional synthesized voices.';
}
function renderExports(){const list=el('downloadList');list.replaceChildren();for(const [kind,item] of exports){const card=document.createElement('article'),link=document.createElement('a');link.href=item.url;link.textContent=item.name;link.target='_blank';link.rel='noopener';if(kind!=='audio')link.download=item.name;card.append(link);list.append(card);}if(!exports.size){const p=document.createElement('p');p.textContent='No exports in this session yet.';list.append(p);}}
function clearExports(){for(const item of exports.values())if(item.local)URL.revokeObjectURL(item.url);exports.clear();renderExports();}
async function rememberExport(item){
 if(!signedIn||!item||!['audio','video','project'].includes(item.kind)||typeof item.url!=='string')return;
 let url=item.url,local=false;
 if(url.startsWith('blob:'+location.origin+'/')){const response=await fetch(url);url=URL.createObjectURL(await response.blob());local=true;}
 else if(item.kind!=='audio'||!url.startsWith('https://'))return;
 if(!signedIn){if(local)URL.revokeObjectURL(url);return;}
 const previous=exports.get(item.kind);if(previous?.local)URL.revokeObjectURL(previous.url);
 exports.set(item.kind,{url,local,name:String(item.name||'ZemaVoice export').slice(0,120)});renderExports();
}
window.addEventListener('zemavoice-auth-state',event=>{
 signedIn=event.detail.signedIn===true;document.body.classList.toggle('signed-in',signedIn);el('workspace').hidden=!signedIn;el('welcome').hidden=signedIn;
 if(!signedIn){for(const id of ['videoTool','dialogueTool'])el(id).removeAttribute('src');clearExports();}
});
window.addEventListener('zemavoice-voices-loaded',event=>{available=event.detail.filter(v=>v&&typeof v.id==='string'&&/^am-[a-z0-9-]+$/.test(v.id)).map(v=>({id:v.id,name:String(v.name||v.id),description:'Provider voice · availability and usage depend on your account.'}));library();});
window.addEventListener('zemavoice-result',event=>{rememberExport(event.detail).catch(()=>{});});
window.addEventListener('message',event=>{if(event.origin!==location.origin||![el('videoTool').contentWindow,el('dialogueTool').contentWindow].includes(event.source))return;if(event.data?.type==='zemavoice-result')rememberExport(event.data).catch(()=>{});});
el('videoTool').onload=sendKey;el('key').addEventListener('input',sendKey);el('forget').addEventListener('click',sendKey);
el('voiceSearch').oninput=library;el('voiceFilter').onchange=library;
window.addEventListener('beforeunload',clearExports);
document.body.classList.toggle('signed-in',signedIn);el('workspace').hidden=!signedIn;el('welcome').hidden=signedIn;library();open('voice');
})();
