"""Experimental human renderer, adapted from the tested v10 pipeline.
Requires a separately installed LatentSync-1.5 checkout, checkpoints and GPU env.
No model installation or downloading occurs inside this entry point.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess


def run(command, **kwargs):
    return subprocess.run(list(map(str, command)), check=True, timeout=1800, **kwargs)


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)], timeout=30))


def render(video, audio, output):
    import cv2
    import numpy as np
    repo = Path(os.environ['LATENTSYNC_REPO']).resolve()
    python = os.environ.get('LATENTSYNC_PYTHON', 'python')
    if not (repo/'checkpoints/latentsync_unet.pt').is_file(): raise ValueError('Model checkpoint missing')
    vprobe, aprobe = probe(video), probe(audio)
    streams = [s for s in vprobe['streams'] if s['codec_type']=='video']
    if not streams or not any(s['codec_type']=='audio' for s in aprobe['streams']): raise ValueError('Missing media streams')
    vduration = float(vprobe['format']['duration'])
    aduration = float(aprobe['format']['duration'])
    if not 0.1 <= aduration <= 30 or not aduration <= vduration <= 120:
        raise ValueError('Narration must be at most 30 seconds and fit inside a video of at most 120 seconds')
    if streams[0]['width']*streams[0]['height'] > 3840*2160: raise ValueError('Input exceeds 4K')
    work = output.parent
    source, speech, wav, raw = [work/name for name in ('source25.mp4','speech.mp4','audio16.wav','generated.mp4')]
    run(['ffmpeg','-y','-v','error','-i',video,'-an','-vf',"scale=w='min(1280,iw)':h='min(720,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,fps=25",'-c:v','libx264','-crf','15',source])
    run(['ffmpeg','-y','-v','error','-i',audio,'-ar','16000','-ac','1',wav])
    pcm = np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',wav,'-f','s16le','pipe:1'],timeout=30),dtype=np.int16)
    audible = np.flatnonzero(np.abs(pcm.astype(np.int32))>80)
    last = (audible[-1]+1)/16000 if len(audible) else 0
    count = math.ceil(aduration*25)
    if last:
        run(['ffmpeg','-y','-v','error','-i',source,'-frames:v',count,'-an','-c:v','libx264','-crf','15',speech])
        # Separate adapter preserves the original official inference script.
        adapter=repo/'scripts/inference_zemavoice.py'
        adapter.write_text((repo/'scripts/inference.py').read_text().replace('torch.cuda.get_device_capability()[0] > 7','torch.cuda.get_device_capability()[0] >= 7'))
        run([python,'-u','-m','scripts.inference_zemavoice','--unet_config_path','configs/unet/stage2.yaml','--inference_ckpt_path','checkpoints/latentsync_unet.pt','--inference_steps','30','--guidance_scale','1.5','--video_path',speech,'--audio_path',wav,'--video_out_path',raw,'--temp_dir',work/'temp','--seed','1247'],cwd=repo)
    original=cv2.VideoCapture(str(source))
    generated=cv2.VideoCapture(str(raw)) if last else None
    n=int(original.get(cv2.CAP_PROP_FRAME_COUNT));width=int(original.get(3));height=int(original.get(4))
    if generated and int(generated.get(cv2.CAP_PROP_FRAME_COUNT)) < count: raise ValueError('Incomplete AI output')
    command=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{width}x{height}','-r','25','-i','pipe:0','-i',wav,'-map','0:v:0','-map','1:a:0','-af','apad','-t',str(n/25),'-c:v','libx264','-crf','15','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',output]
    encoder=subprocess.Popen(list(map(str,command)),stdin=subprocess.PIPE)
    try:
        for i in range(n):
            ok, frame=original.read()
            if not ok: raise ValueError('Source decode failed')
            if generated and i<count:
                ok, ai=generated.read()
                if not ok or ai.shape != frame.shape: raise ValueError('AI frame mismatch')
                # Restore the original silent human footage after speech; no frozen tail.
                start=last+0.04; end=min(aduration,last+0.20)
                u=float(np.clip((i/25-start)/max(end-start,0.001),0,1))
                blend=u*u*(3-2*u)
                frame=np.rint(ai*(1-blend)+frame*blend).astype(np.uint8)
            encoder.stdin.write(frame.tobytes())
        encoder.stdin.close()
        if encoder.wait(timeout=180) != 0: raise ValueError('MP4 encoding failed')
    finally:
        original.release()
        if generated: generated.release()
        if encoder.poll() is None:
            encoder.kill();encoder.wait()

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('video','audio','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    render(args.video.resolve(),args.audio.resolve(),args.output.resolve())
