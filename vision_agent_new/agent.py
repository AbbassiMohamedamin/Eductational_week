import time
import json
import os
from .camera import CameraCapture
from .vlm_client import VLMClient, SceneContext

class VisionAgent:
    def __init__(self, camera: CameraCapture, vlm_client: VLMClient, shared_context_path: str, interval: int = 3):
        self.camera = camera
        self.vlm_client = vlm_client
        self.shared_context_path = shared_context_path
        self.interval = interval

    def run(self):
        print("Starting Vision Agent...")
        try:
            while True:
                scene_context = self.run_once()
                self._write_context(scene_context)
                print(f"Vision Agent update: {scene_context.description}")
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("Vision Agent shutting down...")
            self.camera.release()

    def run_once(self) -> SceneContext:
        frame = self.camera.capture_frame()
        frame_b64 = self.camera.frame_to_base64(frame)
        return self.vlm_client.describe_scene(frame_b64)

    def _write_context(self, context: SceneContext):
        with open(self.shared_context_path, 'w') as f:
            json.dump(context.model_dump(), f, indent=4)
