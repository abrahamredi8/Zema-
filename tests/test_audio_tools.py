from pathlib import Path
import shutil
import subprocess
import pytest


def test_local_volume_preserves_samples_and_protects_peaks():
    if not shutil.which('node'):pytest.skip('Node is required')
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={window:{},Float32Array,ArrayBuffer,DataView,Math,Number,Error};
vm.runInNewContext(fs.readFileSync('public/audio-processing.js','utf8'),context);
const audio=context.window.ZemaVoiceAudio;
const samples=Float32Array.from({length:24000},(_,i)=>.1*Math.sin(2*Math.PI*440*i/24000));
const result=audio.normalize([samples]);
assert.equal(result.channels[0].length,samples.length);
assert(result.gainDb>0);
assert(samples[100]!==result.channels[0][100]); // input remains unchanged
assert(result.peak<.892);
const wav=audio.wav(result.channels,24000),view=new DataView(wav);
assert.equal(view.getUint32(24,true),24000);
assert.equal(view.getUint32(40,true),48000);
const quiet=audio.normalize([new Float32Array(50)]);assert.equal(quiet.gainDb,0);
const peaks=audio.normalize([Float32Array.from([1,0,0,0])],-12);assert(peaks.peak<=10**(-1/20)+1e-7);
const stereo=new DataView(audio.wav([Float32Array.from([1]),Float32Array.from([-1])],24000));
assert.equal(stereo.getInt16(44,true),32767);assert.equal(stereo.getInt16(46,true),-32768);
assert.throws(()=>audio.normalize([Float32Array.from([NaN])]));
'''
    subprocess.run(['node','-e',script],cwd=Path(__file__).resolve().parents[1],check=True)
