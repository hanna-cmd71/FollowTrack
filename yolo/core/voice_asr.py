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
                callback=self._audio_callback,
                blocksize=self.block_size
            )
            self.stream.start()
        except Exception as e:
            print(f"ERROR: Audio stream hardware activation failed: {e}")

    def recognize_speech(self) -> int | None:
        """从队列抽取音频数据，调度 ASR 并返回对齐下位机的模式状态码"""
        if self.model is None or self.audio_queue.empty():
            return None

        try:
            audio_block = self.audio_queue.get_nowait()
            audio_data = np.squeeze(audio_block)

            # 强转数据类型，确保 moonshine 接收到合法的标准 float32 数组
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            text = ""
            # 调度模型前向推理
            if hasattr(self.model, 'moonshine_api') and hasattr(self.model.moonshine_api, 'transcribe'):
                result = self.model.moonshine_api.transcribe(audio_data)
            elif hasattr(self.model, 'transcribe'):
                result = self.model.transcribe(audio_data)
            elif hasattr(self.model, 'Transcript'):
                result = self.model.Transcript(audio_data)
            else:
                result = None

            # ======= 【防御性类型清洗】 =======
            if result is not None:
                # 检查 result 本身是否是 numpy 的数值类型（防止它本身变成 numpy.float32）
                if isinstance(result, (np.ndarray, np.number)):
                    text = ""
                elif hasattr(result, 'text') and isinstance(result.text, str):
                    text = str(result.text)
                elif isinstance(result, dict) and 'text' in result:
                    text = str(result['text'])
                else:
                    # 如果返回的是特殊结构体对象，安全地尝试转为字符串
                    try:
                        text = str(result)
                    except:
                        text = ""

            # 过滤掉干扰字符或无意义的类名
            text = text.strip().replace(" ", "")
            if not text or "Transcript" in text or "Object" in text or len(text) < 1:
                return None

            print(f">>> [Voice Subsystem ASR Output]: {text}")

            # ======= 离散模式状态码转换 =======
            if any(k in text for k in ["追踪", "跟着我", "启动", "过来"]):
                return 0x01  # MODE_TRACK
            elif any(k in text for k in ["休眠", "退下", "停止", "再见"]):
                return 0x03  # MODE_HOME
            elif any(k in text for k in ["开心", "真棒", "乖", "哈哈"]):
                return 0x04  # MODE_HAPPY
            elif any(k in text for k in ["危险", "别动", "救命", "啊"]):
                return 0x05  # MODE_PANIC
            return None
        except Exception as e:
            # 内部静默，防止疯狂打印刷屏阻塞主总线
            return None