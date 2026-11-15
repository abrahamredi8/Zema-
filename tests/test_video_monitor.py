"""Exercise the actual browser controller with stalled network requests."""
from pathlib import Path
import subprocess


def test_stop_and_connection_change_abort_poll_without_resubmission():
    root = Path(__file__).resolve().parents[1]
    script = r"""
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
for(const reason of ['stop','connection','timeout']){
 const elements=new Map(),listeners={},stored=new Map([['zemavoice-last-job','existing-job']]);
 const element=id=>{if(!elements.has(id))elements.set(id,{value:id==='key'?'old-key':'',hidden:false,disabled:false});return elements.get(id);};
 let calls=0,aborted=false;
 const timers=new Map();let nextTimer=0;
 const context={URL,URLSearchParams,AbortController,console,
  location:{search:'',origin:'https://zema.example'},
  document:{getElementById:element,body:{classList:{add(){}}}},
  sessionStorage:{getItem:k=>stored.get(k),setItem:(k,v)=>stored.set(k,v),removeItem:k=>stored.delete(k)},
  setTimeout:(fn,ms)=>{const id=++nextTimer;timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id),
  fetch:(url,options)=>{calls++;assert.equal(url,'/v1/lipsync/jobs/existing-job');assert.equal(options.headers['x-zemavoice-key'],'old-key');
   return new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>{aborted=true;reject(Error('aborted'));},{once:true}));}
 };
 context.window={addEventListener:(name,fn)=>{listeners[name]=fn;}};
 context.window.parent={};
 vm.createContext(context);vm.runInContext(fs.readFileSync('public/video.js','utf8'),context);
 vm.runInContext('ready=true;useJobs=true;',context);
 const pending=element('resume').onclick();
 assert.equal(calls,1);
 if(reason==='stop')element('stop').onclick();
 else if(reason==='connection')listeners.message({origin:context.location.origin,source:context.window.parent,data:{type:'zemavoice-connection',key:''}});
 else [...timers.values()].find(t=>t.ms===30000).fn();
 await pending;
 assert.equal(aborted,true);assert.equal(calls,1,'Must never submit a second render');
 assert.equal(stored.get('zemavoice-last-job'),'existing-job');
 assert.equal(element('check').disabled,false);assert.equal(element('stop').hidden,true);
 assert.match(element('status').textContent,/Resume/);
 assert.equal(timers.size,0,'No leaked request timers');
}
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    subprocess.run(['node', '-e', script], cwd=root, check=True)
