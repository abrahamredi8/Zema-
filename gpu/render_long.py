"""Bound memory for longer narration with overlapping, serial GPU windows."""
import json
import math
from pathlib import Path
import time
from gpu.render_latentsync import render, probe, run, PROFILES


def render_long(video, audio, output, profile='quality', infer=None, chunk_seconds=5):
    video, audio, output = map(lambda p: Path(p).resolve(), (video, audio, output))
    audio_seconds = float(probe(audio)['format']['duration'])
    video_info = probe(video)
    video_seconds = float(video_info['format']['duration'])
    streams = [s for s in video_info['streams'] if s['codec_type']=='video']
    if not streams or streams[0]['width']*streams[0]['height'] > 3840*2160:
        raise ValueError('Video must contain a video stream no larger than 4K')
    if not 0.1 <= audio_seconds <= 30 or not audio_seconds <= video_seconds <= 120:
        raise ValueError('Audio must be at most 30 seconds and fit inside the source video')
    if audio_seconds <= chunk_seconds+0.8:
        return render(video, audio, output, profile, infer)
    started = time.perf_counter()
    root = output.parent/'windows';root.mkdir(parents=True, exist_ok=True)
    source = root/'source25.mp4'
    run(['ffmpeg','-y','-v','error','-i',video,'-an','-vf',"scale=w='min(1280,iw)':h='min(720,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,fps=25",'-c:v','libx264','-crf','15',source])
    frames = int(probe(source)['streams'][0]['nb_frames'])
    speech_frames = min(frames, math.ceil(audio_seconds*25))
    core_frames = round(chunk_seconds*25)
    parts=[]; measurements=[]
    for index, core_start in enumerate(range(0,speech_frames,core_frames)):
        core_end = min(core_start+core_frames,speech_frames)
        # Ten frames of context on either side reduce edge effects. The final
        # video keeps only each core, so no audio is repeated or time-stretched.
        start=max(0,core_start-10);end=min(frames,core_end+10)
        folder=root/str(index);folder.mkdir(exist_ok=True)
        v=folder/'input.mp4';a=folder/'input.wav';result=folder/'result.mp4';part=folder/'core.mp4'
        run(['ffmpeg','-y','-v','error','-i',source,'-vf',f'trim=start_frame={start}:end_frame={end},setpts=N/(25*TB)','-an','-r','25','-c:v','libx264','-crf','15',v])
        run(['ffmpeg','-y','-v','error','-ss',str(start/25),'-i',audio,'-af',f'aresample=24000,apad,atrim=end_sample={(end-start)*960},asetpts=N/(25*TB)','-ar','24000','-ac','1',a])
        measurements.append(render(v,a,result,profile,infer))
        offset=core_start-start
        run(['ffmpeg','-y','-v','error','-i',result,'-vf',f'trim=start_frame={offset}:end_frame={offset+core_end-core_start},setpts=N/(25*TB)','-an','-r','25','-c:v','libx264','-crf','15',part])
        parts.append(part)
    if speech_frames<frames:
        tail=root/'tail.mp4'
        run(['ffmpeg','-y','-v','error','-i',source,'-vf',f'trim=start_frame={speech_frames},setpts=N/(25*TB)','-an','-r','25','-c:v','libx264','-crf','15',tail])
        parts.append(tail)
    listing=root/'parts.txt'
    listing.write_text(''.join("file '"+str(p).replace("'","'\\''")+"'\n" for p in parts))
    # Mux the original complete recording once; chunk AAC timestamps cannot drift.
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',listing,'-i',audio,'-map','0:v:0','-map','1:a:0','-c:v','copy','-af','apad','-t',str(frames/25),'-c:a','aac','-b:a','192k','-movflags','+faststart',output])
    metrics={'profile':profile,'inference_steps':PROFILES[profile],'audio_seconds':audio_seconds,
             'total_seconds':round(time.perf_counter()-started,3),'windows':measurements,
             'window_context_frames':10,'visual_review_required':True}
    (output.parent/'metrics.json').write_text(json.dumps(metrics,indent=2))
    return metrics

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    for name in ('video','audio','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--profile',choices=PROFILES,default='quality')
    args=parser.parse_args()
    render_long(args.video,args.audio,args.output,args.profile)
