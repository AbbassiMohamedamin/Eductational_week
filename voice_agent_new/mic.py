import pyaudio
import numpy as np
import time

class MicCapture:
    def __init__(self, sample_rate=16000, channels=1, chunk_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_open = False
        try:
            self.stream = self.audio.open(format=pyaudio.paInt16,
                                          channels=self.channels,
                                          rate=self.sample_rate,
                                          input=True,
                                          frames_per_buffer=self.chunk_size)
            self.is_open = True
        except Exception as e:
            print(f"Error opening mic: {e}. Mock mode enabled.")

    def record_until_silence(self, threshold=500, silence_duration=1.5) -> bytes:
        if not self.is_open:
            # Mock audio record (empty)
            return b""
            
        frames = []
        silence_start = None
        while True:
            data = self.stream.read(self.chunk_size)
            frames.append(data)
            
            # Simple VAD (energy-based)
            audio_data = np.frombuffer(data, dtype=np.int16)
            if np.max(np.abs(audio_data)) < threshold:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start >= silence_duration:
                    break
            else:
                silence_start = None
                
        return b"".join(frames)

    def close(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
