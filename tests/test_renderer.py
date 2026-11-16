"""Media regression tests use a deterministic fake face renderer, not a GPU."""
import json
import subprocess
from pathlib import Path

import pytest
from gpu.render_latentsync import render


def ffmpeg(*args):
    subprocess.run(['ffmpeg','-y','-v','error',*map(str,args)],check=True)


def test_profile_tail_restoration_and_original_audio_quality(tmp_path, monkeypatch):
    cv2=pytest.importorskip('cv2')
    repo=tmp_path/'model';(repo/'checkpoints').mkdir(parents=True)
    (repo/'checkpoints/latentsync_unet.pt').touch()
    monkeypatch.setenv('LATENTSYNC_REPO',str(repo))
    video=tmp_path/'input.mp4';audio=tmp_path/'input.wav';output=tmp_path/'result.mp4'
    ffmpeg('-f','lavfi','-i','color=c=blue:s=160x120:r=25:d=2','-c:v','libx264',video)
    ffmpeg('-f','lavfi','-i','sine=frequency=440:duration=0.4','-af','apad=whole_dur=1','-ar','24000',audio)
    calls=[]
    def fake_infer(video,audio,output,temp,steps):
        calls.append(steps)
        ffmpeg('-f','lavfi','-i','color=c=red:s=160x120:r=25:d=1','-c:v','libx264',output)
    metrics=render(video,audio,output,'fast',infer=fake_infer)
    assert calls==[20]
    cap=cv2.VideoCapture(str(output))
    cap.set(cv2.CAP_PROP_POS_MSEC,200);ok,early=cap.read();assert ok
    cap.set(cv2.CAP_PROP_POS_MSEC,1400);ok,tail=cap.read();assert ok
    cap.release()
    assert early[:,:,2].mean()>early[:,:,0].mean()+100  # generated red during speech
    assert tail[:,:,0].mean()>tail[:,:,2].mean()+100  # original blue after speech
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(output)]))
    assert next(s for s in probe['streams'] if s['codec_type']=='audio')['sample_rate']=='24000'
    assert metrics['profile']=='fast'


def test_silent_audio_skips_model(tmp_path, monkeypatch):
    pytest.importorskip('cv2')
    repo=tmp_path/'model';(repo/'checkpoints').mkdir(parents=True)
    (repo/'checkpoints/latentsync_unet.pt').touch()
    monkeypatch.setenv('LATENTSYNC_REPO',str(repo))
    video=tmp_path/'input.mp4';audio=tmp_path/'input.wav'
    ffmpeg('-f','lavfi','-i','color=c=blue:s=160x120:r=25:d=1','-c:v','libx264',video)
    ffmpeg('-f','lavfi','-i','anullsrc=r=24000:cl=mono','-t','0.8',audio)
    def forbidden(*args):raise AssertionError('Silent audio must not consume GPU inference')
    render(video,audio,tmp_path/'result.mp4',infer=forbidden)
    assert (tmp_path/'result.mp4').is_file()

def test_long_render_windows_preserve_frame_count_and_audio_timing(tmp_path,monkeypatch):
    cv2=pytest.importorskip('cv2')
    import numpy as np
    from gpu.render_long import render_long
    repo=tmp_path/'model';(repo/'checkpoints').mkdir(parents=True)
    (repo/'checkpoints/latentsync_unet.pt').touch()
    monkeypatch.setenv('LATENTSYNC_REPO',str(repo))
    video=tmp_path/'input.mp4';audio=tmp_path/'input.wav';output=tmp_path/'result.mp4'
    ffmpeg('-f','lavfi','-i','color=c=blue:s=160x120:r=25:d=7','-c:v','libx264',video)
    ffmpeg('-f','lavfi','-i','sine=frequency=440:duration=5.5','-af','apad=whole_dur=6','-ar','24000',audio)
    calls=[]
    def fake_infer(video,audio,output,temp,steps):
        data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(audio)]))
        duration=data['format']['duration'];calls.append(steps)
        ffmpeg('-f','lavfi','-i',f'color=c=red:s=160x120:r=25:d={duration}','-c:v','libx264',output)
    metrics=render_long(video,audio,output,'fast',infer=fake_infer)
    assert calls==[20,20]
    assert len(metrics['windows'])==2
    cap=cv2.VideoCapture(str(output));assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT))==175
    cap.set(cv2.CAP_PROP_POS_MSEC,6800);ok,tail=cap.read();assert ok
    assert tail[:,:,0].mean()>tail[:,:,2].mean()+100
    cap.release()
    def pcm(path):return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-ar','24000','-ac','1','-f','s16le','pipe:1']),dtype=np.int16).astype(float)
    original,decoded=pcm(audio),pcm(output)
    assert np.corrcoef(original,decoded[:len(original)])[0,1]>.99
