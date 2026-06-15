# test_mic.py
import sounddevice as sd
import numpy as np

def print_audio_info():
    print("Available devices:")
    print(sd.query_devices())
    
    print(f"\nDefault input device: {sd.default.device[0]}")
    
    # 测试录音
    duration = 3
    print(f"\nRecording for {duration} seconds...")
    recording = sd.rec(int(duration * 16000), samplerate=16000, channels=1, dtype='float32')
    sd.wait()
    
    energy = np.sqrt(np.mean(recording ** 2))
    print(f"Recording energy: {energy:.4f}")
    
    if energy > 0.01:
        print("✓ Microphone is working!")
    else:
        print("✗ No sound detected - check your microphone")

if __name__ == "__main__":
    print_audio_info()