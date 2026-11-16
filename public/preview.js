/* Development-only visual preview. This does not authenticate API requests. */
function enterPreview(){
 const el=id=>document.getElementById(id);
 el('accountForms').hidden=true;el('accountSignedIn').hidden=false;
 el('accountUser').textContent='Design preview — no account is signed in';
 el('accountStatus').textContent='Preview only. Engine connections are disabled here; no credentials are needed.';
 for(const id of ['key','remember','forget','load','generate'])el(id).disabled=true;
 el('key').value='';
 el('status').textContent='Generation is disabled in this design preview.';
 el('verifyEmail').hidden=true;el('logout').hidden=true;
 const banner=document.createElement('p');banner.className='card';banner.textContent='DEVELOPMENT PREVIEW · Your live website is unchanged.';banner.style.borderColor='#d5a54d';document.querySelector('header').after(banner);
 window.dispatchEvent(new CustomEvent('zemavoice-auth-state',{detail:{signedIn:true}}));
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',enterPreview);else enterPreview();
