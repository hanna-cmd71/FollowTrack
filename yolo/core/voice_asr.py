# core/voice_asr.py
import json
import queue
import numpy as np
import sounddevice as sd
from pathlib import Path

class MoonshineVoiceRecognizer:
    def __init__(self, model_path="models/vosk-model-small-cn"):
        self.audio_queue = queue.Queue(maxsize=5)
        self.sample_rate = 16000
        self.block_size = 8000  # 0.5秒的音频块
        self.stream = None
        self.rec = None
        
        self._init_model(model_path)

    def _init_model(self, model_path):
        """初始化 Vosk 语音识别模型"""
        try:
            from vosk import Model, KaldiRecognizer
            
            # 检查模型是否存在
            model_dir = Path(model_path)
            if not model_dir.exists():
                print(f"WARNING: Model not found at {model_path}")
                print("Please download model from: https://alphacephei.com/vosk/models")
                print("Or run: python download_model.py")
                self.rec = None
                return
            
            model = Model(str(model_dir))
            self.rec = KaldiRecognizer(model, self.sample_rate)
            print(f"INFO: Vosk model loaded successfully from {model_path}")
            
        except ImportError:
            print("ERROR: Vosk not installed. Run: pip install vosk")
            self.rec = None
        except Exception as e:
            print(f"ERROR: Failed to load Vosk model: {e}")
            self.rec = None

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags):
        """音频回调函数"""
        if status:
            print(f"Audio callback status: {status}")
        if not self.audio_queue.full():
            audio_data = indata.copy().flatten()
            self.audio_queue.put(audio_data)

    def start_listening(self, device_id=1):
        """启动音频流监听"""
        try:
            self.stream = sd.InputStream(
                device=device_id,
                samplerate=self.sample_rate,
                channels=1,
                callback=self._audio_callback,
                blocksize=self.block_size,
                dtype=np.float32
            )
            self.stream.start()
            print(f"INFO: Voice stream started on device {device_id}")
            return True
        except Exception as e:
            print(f"ERROR: Audio stream failed: {e}")
            return False

    def _map_command_to_hex(self, text: str) -> int | None:
        """将识别的文本映射到控制命令"""
        if not text:
            return None
        
        text_lower = text.lower().strip()
        
        # 命令映射表
        command_map = [
            # 追踪模式 (0x01)
            (['开始', '启动', '追踪', '跟随', '跟', '追', 'follow', '追综'], 0x01),
            
            # 回正/休眠 (0x03)
            (['home', 'hui zheng', '回正', '归位', '休息', '停止', '停', 'stop', 'sleep', '休眠', '回去'], 0x03),
            
            # 快乐模式 (0x04)
            (['happy', 'kuai le', '快乐', '高兴', '开心', 'yeah', '耶', '胜利', '比耶', '开心模式'], 0x04),
            
            # 惊吓模式 (0x05)
            (['panic', 'jing xia', '惊吓', '害怕', '危险', 'danger', 'three', '三', '三根', '三个'], 0x05),
        ]
        
        for keywords, cmd in command_map:
            for keyword in keywords:
                if keyword in text_lower:
                    print(f"[Worker-Voice] Voice command matched: '{keyword}' in '{text}' -> {hex(cmd)}")
                    return cmd
        
        print(f"[Worker-Voice] Unrecognized voice command: '{text}'")
        return None

    def recognize_speech(self) -> int | None:
        """识别语音并返回命令代码"""
        try:
            # 获取音频数据
            audio_block = self.audio_queue.get_nowait()
            
            if len(audio_block) == 0 or self.rec is None:
                return None
            
            # 转换为 int16 格式（Vosk 需要）
            int16_data = (audio_block * 32767).astype(np.int16)
            
            # 处理音频数据
            if self.rec.AcceptWaveform(int16_data.tobytes()):
                result = json.loads(self.rec.Result())
                text = result.get('text', '')
                
                if text and len(text) > 0:
                    print(f"[Worker-Voice] Recognized: '{text}'")
                    return self._map_command_to_hex(text)
                    
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[Worker-Voice] ERROR: Speech recognition error: {e}")
        
        return None

    def stop_listening(self):
        """停止音频流"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            print("INFO: Voice stream stopped")