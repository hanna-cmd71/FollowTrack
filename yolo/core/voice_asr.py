from queue import Queue
import numpy as np
import sounddevice as sd


class MoonshineVoiceRecognizer:

    def __init__(self):
        """初始化音频缓冲队列"""
        self.audio_queue = Queue()
        self.sample_rate = 16000
        self.block_size = 16000
        self.stream = None
        self.model = None
        self._init_model()

    def _init_model(self):
        try:
            import moonshine_voice
            if hasattr(moonshine_voice, 'Transcript'):
                self.model = moonshine_voice
                print("INFO: Successfully bound to moonshine_voice Transcript API.")
            else:
                self.model = None
                print("WARNING: Transcript core not found. Voice recognition enters fallback.")
        except Exception as e:
            print(f"ERROR: Failed to initialize moonshine_voice engine: {e}")
            self.model = None

    def _audio_callback(self, indata: np.ndarray, frames: int, 
                        time_info: dict, status: sd.CallbackFlags):
        """音频硬件中断底层的回调函数，将数字音频流数据推入缓冲队列。"""
        self.audio_queue.put(indata.copy())

    def start_listening(self):
        """建立音频捕获上下文输入流，拉起硬件录音常驻缓冲区。"""
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                blocksize=self.block_size,
                callback=self._audio_callback
            )
            self.stream.start()
            print("INFO: Audio subsystem peripheral device is actively listening.")
        except Exception as e:
            print(f"ERROR: Audio capture hardware stream opening failed: {e}")
            self.stream = None

    def get_keyword_command(self) -> int | None:
        """从音频队列提取数据并转写，根据关键字输出契合下位机状态机的控制码。"""
        if self.model is None or self.audio_queue.empty():
            return None

        try:
            audio_block = self.audio_queue.get()
            audio_data = np.squeeze(audio_block)

            text = ""
            if hasattr(self.model, 'moonshine_api') and hasattr(self.model.moonshine_api, 'transcribe'):
                result = self.model.moonshine_api.transcribe(audio_data)
            elif hasattr(self.model, 'transcribe'):
                result = self.model.transcribe(audio_data)
            elif hasattr(self.model, 'Transcript'):
                result = self.model.Transcript(audio_data)
            else:
                result = None

            if result is not None:
                if hasattr(result, 'text'):
                    text = str(result.text)
                elif isinstance(result, dict) and 'text' in result:
                    text = str(result['text'])
                else:
                    text = str(result)

            text = text.strip().replace(" ", "")

            if not text or "Transcript" in text or len(text) < 1:
                return None

            print(f">>> [Voice Subsystem ASR Output]: {text}")

            if any(k in text for k in ["追踪", "跟着我", "启动", "过来"]):
                return 0x01
            elif any(k in text for k in ["休眠", "退下", "停止", "再见"]):
                return 0x03
            elif any(k in text for k in ["开心", "真棒", "乖"]):
                return 0x04
            elif any(k in text for k in ["危险", "躲开", "吓一跳"]):
                return 0x05
        except Exception:
            pass
            
        return None