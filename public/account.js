'use strict';
const $=id=>document.getElementById(id);
async function requestAuth(path,body){
 const opts={method:path==='me'?'GET':'POST',credentials:'same-origin',headers:{'content-type':'application/json'}};
 if(body)opts.body=JSON.stringify(body);
 const r=await fetch('/auth/'+path,opts);const j=await r.json();if(!r.ok)throw Error(typeof j.detail==='string'?j.detail:'Request failed');return j;
}
async function refreshAccount(){try{const me=await requestAuth('me');$('accountUser').textContent='Signed in as '+me.email;$('accountForms').hidden=true;$('accountSignedIn').hidden=false;}catch(e){$('accountForms').hidden=false;$('accountSignedIn').hidden=true;}}
$('accountForm').onsubmit=async e=>{e.preventDefault();const button=$('accountSubmit');button.disabled=true;try{const mode=$('accountMode').value;const email=$('accountEmail').value,password=$('accountPassword').value;const result=await requestAuth(mode,{email,password});$('accountStatus').textContent=result.message;$('accountPassword').value='';await refreshAccount();}catch(err){$('accountStatus').textContent=err.message;}finally{button.disabled=false;}};
$('accountMode').onchange=()=>{$('accountSubmit').textContent=$('accountMode').value==='register'?'Create account':'Sign in';};
$('logout').onclick=async()=>{try{await requestAuth('logout');$('accountStatus').textContent='Signed out';await refreshAccount();}catch(e){$('accountStatus').textContent=e.message;}};
refreshAccount();
