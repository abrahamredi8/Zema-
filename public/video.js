'use strict';
const el=id=>document.getElementById(id);
let ready=false, useJobs=false, resultUrl, monitoring=false;
const storageKey='zemavoice-last-job';
function savedJob(){try{return sessionStorage.getItem(storageKey);}catch{return null;}}
function saveJob(id){el('forget').hidden=false;try{sessionStorage.setItem(storageKey,id);}catch{}}
function clearJob(){el('forget').hidden=true;try{sessionStorage.removeItem(storageKey);}catch{}}
function headers(){return {'x-zemavoice-key':el('key').value};}
function message(text){el('status').textContent=text;}
function busy(value){el('render').disabled=value||!ready;el('check').disabled=value;el('key').disabled=value;el('resume').disabled=value||!ready;el('forget').disabled=value;}
async function errorText(response){try{const data=await response.json();return typeof data.detail==='string'?data.detail:'Request failed.';}catch{return 'Request failed (HTTP '+response.status+').';}}
async function showResult(response){if(!response.ok)throw Error(await errorText(response));if(!response.headers.get('content-type')?.startsWith('video/mp4'))throw Error('The server did not return an MP4.');const blob=await response.blob();if(resultUrl)URL.revokeObjectURL(resultUrl);resultUrl=URL.createObjectURL(blob);el('result').src=resultUrl;el('result').hidden=false;el('download').href=resultUrl;el('download').hidden=false;message('Video ready. Play it below and check lip timing, pauses, and the ending.');if(window.parent!==window)window.parent.postMessage({type:'zemavoice-result',kind:'video',url:resultUrl,name:'zemavoice-lipsync.mp4'},location.origin);}
async function monitor(id){
    monitoring=true;el('stop').hidden=false;el('progress').hidden=false;
    try{
        while(monitoring){
            const response=await fetch('/v1/lipsync/jobs/'+encodeURIComponent(id),{headers:headers()});
            if(!response.ok)throw Error(await errorText(response));
            const job=await response.json();
            if(!monitoring)break;
            el('progress').value=job.progress;
            message('Render '+id+': '+job.status+' ('+job.progress+'%). You can resume this job in this tab after reloading.');
            if(job.status==='succeeded'){
                await showResult(await fetch('/v1/lipsync/jobs/'+encodeURIComponent(id)+'/result',{headers:headers()}));
                clearJob();el('resume').hidden=true;return;
            }
            if(job.status==='failed'||job.status==='cancelled'){clearJob();el('resume').hidden=true;throw Error('Render '+job.status+'. Check your source files before submitting a new job.');}
            await new Promise(resolve=>setTimeout(resolve,4000));
        }
        message('Progress checks stopped. The GPU job may still be running; use Resume last render to check it.');
    }finally{monitoring=false;el('stop').hidden=true;el('progress').hidden=true;}
}
el('key').oninput=()=>{ready=false;el('render').disabled=true;el('resume').disabled=true;};
el('check').onclick=async()=>{busy(true);ready=false;try{const response=await fetch('/v1/lipsync/status',{headers:headers()});if(!response.ok)throw Error(await errorText(response));const data=await response.json();useJobs=data.jobs_configured===true;ready=useJobs||data.configured===true;message(ready?(useJobs?'Job service is configured. Submit a short test to verify GPU rendering.':'Short-test engine is configured. Long scenes require the job service.'):'The GPU engine is not connected yet. Your files have not been uploaded.');el('resume').hidden=!useJobs||!savedJob();}catch(error){message(error.message);}finally{busy(false);}};
el('stop').onclick=()=>{monitoring=false;el('stop').disabled=true;};
el('resume').onclick=async()=>{const id=savedJob();if(!id||!ready||!useJobs)return;busy(true);el('stop').disabled=false;try{await monitor(id);}catch(error){message(error.message+' Use Resume to retry checking; this does not submit another render.');}finally{busy(false);}};
el('renderForm').onsubmit=async event=>{
    event.preventDefault();if(!ready)return;
    if(useJobs&&savedJob()){message('A previous render is saved in this tab. Resume it before submitting another job.');el('resume').hidden=false;return;}
    const video=el('video').files[0],audio=el('audio').files[0];if(!video||!audio)return;
    if(video.size+audio.size+65536>40*1024*1024){message('Combined upload is too large. Choose smaller files.');return;}
    busy(true);el('stop').disabled=false;el('result').hidden=true;el('download').hidden=true;
    message('Uploading… Keep this page open.');
    try{
        const form=new FormData();form.append('video',video);form.append('audio',audio);
        const response=await fetch(useJobs?'/v1/lipsync/jobs?profile='+encodeURIComponent(el('profile').value):'/v1/lipsync/render',{method:'POST',headers:headers(),body:form});
        if(!response.ok)throw Error(await errorText(response));
        if(useJobs){const job=await response.json();saveJob(job.job_id);el('resume').hidden=false;await monitor(job.job_id);}else await showResult(response);
    }catch(error){message(error.message+' No finished video was received. If the upload was interrupted, the engine may have accepted it; check before submitting again.');}
    finally{busy(false);}
};
window.addEventListener('beforeunload',()=>{if(resultUrl)URL.revokeObjectURL(resultUrl);});

el('forget').hidden=!savedJob();
el('forget').onclick=()=>{if(window.confirm('Forget this job reference? This does not cancel the GPU job. You may lose access to its result.')){clearJob();el('resume').hidden=true;message('Saved job reference removed from this tab.');}};

window.addEventListener('message',event=>{if(event.origin!==location.origin||event.source!==window.parent||event.data?.type!=='zemavoice-connection')return;el('key').value=String(event.data.key||'');ready=false;el('render').disabled=true;el('resume').disabled=true;});
