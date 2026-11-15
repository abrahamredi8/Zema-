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
