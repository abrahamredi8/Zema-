# Adapted from ByteDance LatentSync scripts/inference.py.
# Copyright (c) 2024 Bytedance Ltd. and/or its affiliates.
# Licensed under the Apache License, Version 2.0.
# https://www.apache.org/licenses/LICENSE-2.0
"""Lazy process-resident pipeline for a single serial GPU worker."""
from contextlib import contextmanager
import os
from pathlib import Path
import sys
import time

@contextmanager
def repo_directory(repo):
    previous = Path.cwd()
    os.chdir(repo)
    try:
        yield
    finally:
        os.chdir(previous)

class LatentSyncBackend:
    def __init__(self):
        self.pipeline = None
        self.load_seconds = 0
        self.load_count = 0
        self.detectors = {}

    def infer(self, video, audio, output, temp, steps):
        repo = Path(os.environ['LATENTSYNC_REPO']).resolve()
        if str(repo) not in sys.path: sys.path.insert(0, str(repo))
        with repo_directory(repo):
            if self.pipeline is None:
                started = time.perf_counter()
                import torch
                from omegaconf import OmegaConf
                from diffusers import AutoencoderKL, DDIMScheduler
                from accelerate.utils import set_seed
                from latentsync.models.unet import UNet3DConditionModel
                from latentsync.pipelines.lipsync_pipeline import LipsyncPipeline
                from latentsync.whisper.audio2feature import Audio2Feature
                if not torch.cuda.is_available(): raise RuntimeError('CUDA GPU required')
                config = OmegaConf.load('configs/unet/stage2.yaml')
                dtype = torch.float16 if torch.cuda.get_device_capability()[0] >= 7 else torch.float32
                checkpoint = {768:'small',384:'tiny'}[config.model.cross_attention_dim]
                encoder = Audio2Feature(model_path=f'checkpoints/whisper/{checkpoint}.pt', device='cuda',
                    num_frames=config.data.num_frames, audio_feat_length=config.data.audio_feat_length)
                vae = AutoencoderKL.from_pretrained('stabilityai/sd-vae-ft-mse', torch_dtype=dtype, local_files_only=True)
                vae.config.scaling_factor = 0.18215
                vae.config.shift_factor = 0
                unet, _ = UNet3DConditionModel.from_pretrained(OmegaConf.to_container(config.model),
                    'checkpoints/latentsync_unet.pt', device='cpu')
                pipeline = LipsyncPipeline(vae=vae, audio_encoder=encoder, unet=unet.to(dtype=dtype),
                    scheduler=DDIMScheduler.from_pretrained('configs')).to('cuda')
                self.pipeline, self.config, self.dtype = pipeline, config, dtype
                self.set_seed = set_seed
                self.load_seconds = time.perf_counter() - started
                self.load_count += 1
            self.set_seed(1247)
            cfg = self.config
            # Reuse detector weights, but create a fresh ImageProcessor/restorer on
            # every call so temporal smoothing history never crosses videos.
            from latentsync.utils import image_processor
            detector_factory = image_processor.FaceDetector
            def cached_detector(device="cuda"):
                if device not in self.detectors:
                    self.detectors[device] = detector_factory(device=device)
                return self.detectors[device]
            image_processor.FaceDetector = cached_detector
            try:
                self.pipeline(video_path=str(video), audio_path=str(audio), video_out_path=str(output),
                    num_frames=cfg.data.num_frames, num_inference_steps=steps, guidance_scale=1.5,
                    weight_dtype=self.dtype, width=cfg.data.resolution, height=cfg.data.resolution,
                    mask_image_path=cfg.data.mask_image_path, temp_dir=str(temp))
            finally:
                image_processor.FaceDetector = detector_factory
