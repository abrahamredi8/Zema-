"""Blender helper: apply ZemaVoice mouth animation to a character rig.

Run from Blender's scripting environment after selecting an object with
shape keys named 'jawOpen' and optionally 'mouthClose'. This supports both
cartoon and realistic *rigged* models; it does not perform face tracking.
"""
import bpy
import json
from pathlib import Path

TIMELINE_JSON = "/path/to/zemavoice_lipsync.json"  # edit in Blender
OBJECT_NAME = "CharacterFace"  # edit to your rigged mesh name

def apply_timeline(path, object_name):
    obj = bpy.data.objects.get(object_name)
    if not obj or not obj.data.shape_keys:
        raise ValueError("Character object with shape keys not found")
    keys = obj.data.shape_keys.key_blocks
    if "jawOpen" not in keys:
        raise ValueError("Required shape key 'jawOpen' missing")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    fps = data["fps"]
    bpy.context.scene.render.fps = fps
    for item in data["frames"]:
        frame = int(item["frame"]) + 1
        for name, value in item["blendshapes"].items():
            if name in keys:
                keys[name].value = value
                keys[name].keyframe_insert(data_path="value", frame=frame)
    bpy.context.scene.frame_end = len(data["frames"])
    print("Applied", len(data["frames"]), "lip-sync frames")

if __name__ == "__main__":
    apply_timeline(TIMELINE_JSON, OBJECT_NAME)
