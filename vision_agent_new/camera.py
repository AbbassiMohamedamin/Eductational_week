import cv2
import base64
import numpy as np
import os

class CameraCapture:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Warning: No webcam found. Falling back to test image mode.")

    def capture_frame(self) -> np.ndarray:
        if not self.cap.isOpened():
            # Mock frame: a simple color image
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        ret, frame = self.cap.read()
        if not ret:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        return frame

    def frame_to_base64(self, frame: np.ndarray) -> str:
        _, buffer = cv2.imencode('.jpg', frame)
        return base64.b64encode(buffer).decode('utf-8')

    def release(self):
        if self.cap.isOpened():
            self.cap.release()
