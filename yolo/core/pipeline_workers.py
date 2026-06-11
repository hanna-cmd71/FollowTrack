import time
from multiprocessing import Queue, Value
import cv2
import numpy as np
from core.face_yolo import FaceYOLO
from core.hand_mp import HandDetector
from core.voice_asr import MoonshineVoiceRecognizer


"""core/pipeline_workers.py 的 run_hand_perception 函数"""
def run_hand_perception(frame_queue: Queue, is_tracking: Value, h_mode: Value, h_scale: Value):
    hand_det = HandDetector()
    print("INFO: [Worker-Hand] MediaPipe engine thread active.")

    track_confirm_count = 0
    home_confirm_count = 0
    DEBOUNCE_THRESHOLD = 3  

    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            if frame is None:
                break

            small_frame = cv2.resize(frame, (320, 240))
            res_mode, _, _, res_scale = hand_det.get_control_signal(small_frame)

            if res_mode != 0x00 and isinstance(res_scale, (int, float)) and res_scale > 0:
            
                h_scale.value = float(0.3 * res_scale + 0.7 * h_scale.value)

            if res_mode == 0x01: 
                track_confirm_count += 1
                home_confirm_count = 0
                if track_confirm_count >= DEBOUNCE_THRESHOLD:
                    if h_mode.value != 0x01:
                        h_mode.value = 0x01
                        is_tracking.value = 1
                        print("INFO: [Hand-State] Gesture Confirmed -> MODE_TRACK")
            elif res_mode == 0x03:  
                home_confirm_count += 1
                track_confirm_count = 0
                if home_confirm_count >= DEBOUNCE_THRESHOLD:
                    if h_mode.value != 0x03:
                        h_mode.value = 0x03
                        is_tracking.value = 0
                        print("INFO: [Hand-State] Gesture Confirmed -> MODE_HOME")
            else:
                # 如果是 0x00(无手) 或 0x02(模糊状态)，清空确认计数器，保持当前行为，不盲目覆盖
                track_confirm_count = 0
                home_confirm_count = 0

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
                try:
                    latest_frame = frame_queue.get_nowait()
                except:
                    break
        
            if latest_frame is None:
                time.sleep(0.002)
                continue

            # 缩放分辨率至边缘端专用尺寸
            small_frame = cv2.resize(latest_frame, (320, 240))
            
            # 执行前向回归
            _, dx, dy, _ = face_det.get_control_signal(small_frame)

            # 原子注入多进程总线
            out_dx.value = int(dx)
            out_dy.value = int(dy)
        else:
            time.sleep(0.002) # 极高频轮询，不放过任何新帧


def run_voice_asr(is_tracking: Value, h_mode: Value):
    try:
        m_vr = MoonshineVoiceRecognizer()
        m_vr.start_listening()
        print("INFO: [Worker-Voice] Moonshine ASR engine listener active.")
    except Exception as e:
        print(f"WARNING: [Worker-Voice] Peripheral audio driver initialization failed: {e}")
        return

    while True:
        try:
            # 【核心修复点】：将原先错误的 get_keyword_command() 改为您真实的 recognize_speech()
            cmd_code = m_vr.recognize_speech()
            
            if cmd_code is not None:
                # 只有识别出有效动作时才修改状态机，防止 None 覆盖正常状态
                if cmd_code == 0x01:    # 启动/追踪
                    is_tracking.value = 1
                    h_mode.value = 0x01
                elif cmd_code == 0x03:  # 休眠/退下
                    is_tracking.value = 0
                    h_mode.value = 0x03
                elif cmd_code in [0x04, 0x05]: # 快乐笑脸 或 惊吓 Panic 模式
                    # 在这两种特殊模式下，由决策树决定是否继续保持视觉追踪
                    h_mode.value = cmd_code
                
                print(f"INFO: [Worker-Voice] State Synced -> mode: {hex(h_mode.value)}, tracking: {is_tracking.value}")
        except Exception as e:
            print(f"WARNING: [Worker-Voice] Process cycle inner exception: {e}")
        
        # 释放 CPU，给音频采集硬件流留出缓冲时间
        time.sleep(0.1)