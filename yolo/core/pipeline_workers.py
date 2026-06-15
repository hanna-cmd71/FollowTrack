import time
from multiprocessing import Queue, Value
import cv2
from core.face_yolo import FaceYOLO
from core.hand_mp import HandDetector
from core.voice_asr import MoonshineVoiceRecognizer


def run_hand_perception(frame_queue: Queue, is_tracking: Value, h_mode: Value, h_scale: Value):
    hand_det = HandDetector()
    print("INFO: [Worker-Hand] MediaPipe engine thread active.")

    # 状态消抖计数器配置
    counters = {0x01: 0, 0x03: 0, 0x04: 0, 0x05: 0}
    DEBOUNCE_THRESHOLD = 3  # 连续 3 帧确认才发生状态跳转

    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            if frame is None:
                break

            small_frame = cv2.resize(frame, (320, 240))
            res_mode, _, _, res_scale = hand_det.get_control_signal(small_frame)

            # 景深平滑滤波
            if res_mode != 0x00 and isinstance(res_scale, (int, float)) and res_scale > 0:
                h_scale.value = float(0.3 * res_scale + 0.7 * h_scale.value)

            # 状态消抖流转控制
            for mode_code in counters.keys():
                if res_mode == mode_code:
                    counters[mode_code] += 1
                    if counters[mode_code] >= DEBOUNCE_THRESHOLD:
                        if h_mode.value != mode_code:
                            h_mode.value = mode_code
                            # 【关键特性】：触发追踪(0x01)、快乐(0x04)或惊吓(0x05)时，均需强开人脸子进程消费
                            if mode_code in [0x01, 0x04, 0x05]:
                                is_tracking.value = 1
                            elif mode_code == 0x03:
                                is_tracking.value = 0
                            print(f"INFO: [Hand-State] Gesture Confirmed -> {hex(mode_code)}")
                else:
                    counters[mode_code] = 0
        else:
            time.sleep(0.01)


def run_face_tracking(frame_queue: Queue, is_tracking: Value, out_dx: Value, out_dy: Value, model_path: str):
    face_det = FaceYOLO(model_path)
    print("INFO: [Worker-Face] YOLOv8 CUDA engine thread active.")

    while True:
        if is_tracking.value == 0:
            while not frame_queue.empty():
                try: frame_queue.get_nowait()
                except: break
            time.sleep(0.02)
            continue

        if not frame_queue.empty():
            latest_frame = None
            while not frame_queue.empty():
                try: latest_frame = frame_queue.get_nowait()
                except: break
        
            if latest_frame is None:
                time.sleep(0.002)
                continue

            small_frame = cv2.resize(latest_frame, (320, 240))
            _, dx, dy, _ = face_det.get_control_signal(small_frame)

            out_dx.value = int(dx)
            out_dy.value = int(dy)
        else:
            time.sleep(0.002)


def run_voice_asr(is_tracking: Value, h_mode: Value):
    """语音识别工作进程 - 使用Vosk"""
    try:
        # 导入语音识别器
        from core.voice_asr import MoonshineVoiceRecognizer
        
        # 初始化
        m_vr = MoonshineVoiceRecognizer()
        
        # 使用设备1（您的USB麦克风）
        if not m_vr.start_listening(device_id=1):
            print("WARNING: [Worker-Voice] Failed to start voice stream. Voice control disabled.")
            while True:
                time.sleep(1)
            return
            
        print("INFO: [Worker-Voice] Vosk ASR engine listener active.")
        
    except Exception as e:
        print(f"WARNING: [Worker-Voice] Initialization failed: {e}")
        while True:
            time.sleep(1)
        return
    
    last_command_time = 0
    command_cooldown = 1.0  # 命令冷却时间（秒）
    
    while True:
        try:
            current_time = time.time()
            
            # 语音识别（非阻塞）
            cmd_code = m_vr.recognize_speech()
            
            if cmd_code is not None and current_time - last_command_time >= command_cooldown:
                last_command_time = current_time
                
                # 根据命令更新状态
                if cmd_code == 0x01:  # TRACK
                    is_tracking.value = 1
                    h_mode.value = 0x01
                    print(f"[Worker-Voice] TRACK mode activated")
                    
                elif cmd_code == 0x03:  # HOME/SLEEP
                    is_tracking.value = 0
                    h_mode.value = 0x03
                    print(f"[Worker-Voice] HOME mode activated")
                    
                elif cmd_code == 0x04:  # HAPPY
                    is_tracking.value = 1
                    h_mode.value = 0x04
                    print(f"[Worker-Voice] HAPPY mode activated")
                    
                elif cmd_code == 0x05:  # PANIC
                    is_tracking.value = 1
                    h_mode.value = 0x05
                    print(f"[Worker-Voice] PANIC mode activated")
                    
        except Exception as e:
            print(f"WARNING: [Worker-Voice] Error: {e}")
            
        time.sleep(0.1)