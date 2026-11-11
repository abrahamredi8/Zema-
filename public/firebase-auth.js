import {initializeApp} from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js';
import {getAuth,onAuthStateChanged,createUserWithEmailAndPassword,signInWithEmailAndPassword,signInWithPopup,signInWithRedirect,getRedirectResult,GoogleAuthProvider,signOut,sendPasswordResetEmail,sendEmailVerification} from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js';

const firebaseConfig={
 apiKey:'AIzaSyA6L4yKT_B9ZP3zKDM-yYbe-Mj2shkT_D0',
 authDomain:'zemavoice-ai.firebaseapp.com',
 projectId:'zemavoice-ai',
 storageBucket:'zemavoice-ai.firebasestorage.app',
 messagingSenderId:'50302670735',
 appId:'1:50302670735:web:17a6444cbe4bc905035dfa',
 measurementId:'G-EHRCKVGN0F'
};
const auth=getAuth(initializeApp(firebaseConfig));
const $=id=>document.getElementById(id);
function status(message){$('accountStatus').textContent=message;}
function friendly(error){
 const code=error?.code||'';
 const messages={
 'auth/email-already-in-use':'An account already exists with this email. Choose Sign in.',
 'auth/invalid-email':'Enter a valid email address.',
 'auth/weak-password':'Choose a stronger password.',
 'auth/invalid-credential':'Incorrect email or password.',
 'auth/popup-closed-by-user':'Google sign-in was cancelled.',
 'auth/unauthorized-domain':'This website domain is not authorized in Firebase.',
 'auth/operation-not-allowed':'This sign-in method is not enabled in Firebase.',
 'auth/too-many-requests':'Too many attempts. Please try again later.',
 'auth/account-exists-with-different-credential':'This email uses a different sign-in method. Sign in with that method first.'
 };
 return messages[code]||('Sign-in error: '+(code||'Please try again.'));
}
onAuthStateChanged(auth,user=>{
 $('accountForms').hidden=!!user;
 $('accountSignedIn').hidden=!user;
 if(user){$('accountUser').textContent='Signed in as '+(user.email||'ZemaVoice user');status(user.emailVerified?'Signed in.':'Signed in. Verify your email when possible.');}
 else{status('Sign in to your ZemaVoice account.');}
});
$('accountMode').onchange=()=>{
 const register=$('accountMode').value==='register';
 $('accountSubmit').textContent=register?'Create account':'Sign in';
 $('accountPassword').autocomplete=register?'new-password':'current-password';
};
$('accountForm').onsubmit=async event=>{
 event.preventDefault();
 const button=$('accountSubmit');button.disabled=true;
 try{
 const email=$('accountEmail').value.trim(),password=$('accountPassword').value;
 if($('accountMode').value==='register'){
  const result=await createUserWithEmailAndPassword(auth,email,password);
  try{await sendEmailVerification(result.user);status('Account created! Verification email sent.');}
  catch(e){status('Account created. Email verification could not be sent yet.');}
 }else{
  await signInWithEmailAndPassword(auth,email,password);status('Signed in successfully.');
 }
 $('accountPassword').value='';
 }catch(e){status(friendly(e));}finally{button.disabled=false;}
};
$('googleSignIn').onclick=async()=>{
 const b=$('googleSignIn');b.disabled=true;
 try{
  const provider=new GoogleAuthProvider();
  try{await signInWithPopup(auth,provider);}
  catch(e){if(['auth/popup-blocked','auth/operation-not-supported-in-this-environment'].includes(e.code)){await signInWithRedirect(auth,provider);return;}throw e;}
  status('Signed in with Google.');
 }catch(e){status(friendly(e));}finally{b.disabled=false;}
};
getRedirectResult(auth).catch(e=>status(friendly(e)));
$('resetPassword').onclick=async()=>{
 const email=$('accountEmail').value.trim();
 if(!email){status('Enter your email address first, then tap Reset password.');return;}
 try{await sendPasswordResetEmail(auth,email);status('If this email is eligible, a reset email will arrive shortly.');}
 catch(e){status(friendly(e));}
};
$('logout').onclick=async()=>{try{await signOut(auth);status('Signed out.');}catch(e){status(friendly(e));}};
$('verifyEmail').onclick=async()=>{
 if(!auth.currentUser)return;
 try{await sendEmailVerification(auth.currentUser);status('Verification email sent.');}
 catch(e){status(friendly(e));}
};
