/* Development-only visual preview. This does not authenticate API requests. */
window.addEventListener('DOMContentLoaded',()=>{
 const el=id=>document.getElementById(id);
 el('accountForms').hidden=true;el('accountSignedIn').hidden=false;
 el('accountUser').textContent='Design preview — no account is signed in';
 el('accountStatus').textContent='Preview only. Generation still requires a private engine connection.';
 el('verifyEmail').hidden=true;el('logout').hidden=true;
 const banner=document.createElement('p');banner.className='card';banner.textContent='DEVELOPMENT PREVIEW · Your live website is unchanged.';banner.style.borderColor='#d5a54d';document.querySelector('header').after(banner);
 window.dispatchEvent(new CustomEvent('zemavoice-auth-state',{detail:{signedIn:true}}));
});
