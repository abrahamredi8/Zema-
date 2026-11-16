"""Run both profiles on identical media in one resident model process."""
import argparse
import json
import shutil
from pathlib import Path
from gpu.latentsync_backend import LatentSyncBackend
from gpu.render_latentsync import render


def benchmark(video, audio, output):
    backend = LatentSyncBackend()
    results = []
    # Quality first matches the baseline. Fast follows with the model resident.
    # Run quality again to distinguish cold loading from profile speed differences.
    for name, profile in [('quality_cold','quality'),('fast_warm','fast'),('quality_warm','quality')]:
        folder = output/name
        folder.mkdir(parents=True, exist_ok=True)
        loads_before = backend.load_count
        metrics = render(video, audio, folder/'result.mp4', profile, infer=backend.infer)
        metrics.update(run=name, model_loaded_this_run=backend.load_count>loads_before,
                       model_load_seconds=round(backend.load_seconds,3) if backend.load_count>loads_before else 0)
        results.append(metrics)
        (output/'benchmark.json').write_text(json.dumps({'runs':results, 'visual_review_required':True},indent=2))
        print(json.dumps(metrics),flush=True)
        for path in folder.iterdir():
            if path.name not in ('result.mp4','metrics.json'):
                if path.is_dir():shutil.rmtree(path)
                else:path.unlink()
    return results

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('video','audio','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    benchmark(args.video.resolve(),args.audio.resolve(),args.output.resolve())
