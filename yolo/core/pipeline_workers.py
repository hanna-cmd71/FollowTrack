import time
from multiprocessing import Queue, Value
import cv2
import numpy as np
from core.face_yolo import FaceYOLO
from core.hand_mp import HandDetector
from core.voice_asr import MoonshineVoiceRecognizer


def run_hand_perception(frame_queue: Queue, is_tracking: Value, h_mode: Value, h_scale: Value):
    hand_det = HandDetector()
    print("INFO: [Worker-Hand] MediaPipe engine thread active.")

    locked_state = 0x02
    track_frame_count = 0
    sleep_frame_count = 0
    REQUIRED_FRAMES = 5

    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            if frame is None:
                break

            small_frame = cv2.resize(frame, (320, 240))
            res_mode, _, _, res_scale = hand_det.get_control_signal(small_frame)

            if (res_mode != 0x00 and 
                isinstance(res_scale, (int, float)) and res_scale > 0):
                h_scale.value = float(res_scale)

            match res_mode:
                case 0x01:  
                    track_frame_count += 1
                    sleep_frame_count = 0
                case 0x03:  
                    sleep_frame_count += 1
                    track_frame_count = 0
                case 0x02 | 0x00:  # 模糊手势 或 目标丢失（空转保护锁）
                    # 计数器清零，但绝对不撤销、不重置当前的运行状态锁！
                    track_frame_count = 0
                    sleep_frame_count = 0
                case _:  # 缺省兜底安全拦截
                    track_frame_count = 0
                    sleep_frame_count = 0

            # --- 迟滞状态机时序窗口判决 ---
            if track_frame_count >= REQUIRED_FRAMES and locked_state != 0x01:
                locked_state = 0x01
                is_tracking.value = 1
                h_mode.value = 0x01
                print(">>> [Hysteresis Filter]: State flip to [TRACKING].")
                track_frame_count = 0
            elif sleep_frame_count >= REQUIRED_FRAMES and locked_state != 0x02:
                locked_state = 0x02
                is_tracking.value = 0
                h_mode.value = 0x03
                print(">>> [Hysteresis Filter]: State flip to [SLEEPY].")
                sleep_frame_count = 0

            if locked_state == 0x01 and res_mode != 0x01:
                h_mode.value = 0x01
        else:
            time.sleep(0.005)


def run_face_tracking(frame_queue: Queue, is_tracking: Value, out_dx: Value, out_dy: Value, model_path: str):
    
    face_det = FaceYOLO(model_path)
    print("INFO: [Worker-Face] YOLOv8 CUDA engine thread active.")

    while True:
        # 静态拦截：系统未进入追踪状态时挂起，定时清空死帧缓冲队列，杜绝数据积压时延
        if is_tracking.value == 0:
            while not frame_queue.empty():
                try:
                    frame_queue.get_nowait()
                except:
                    break
            time.sleep(0.02)
            continue

        if not frame_queue.empty():
            frame = frame_queue.get()
            if frame is None:
                break

            small_frame = cv2.resize(frame, (320, 240))
            _, dx, dy, _ = face_det.get_control_signal(small_frame)

            out_dx.value = dx
            out_dy.value = dy
        else:
            time.sleep(0.005)


def run_voice_asr(is_tracking: Value, h_mode: Value):
    """高级语音流特征解析后台进程，调度本地大模型环境进行上下文情感匹配。"""
    try:
        m_vr = MoonshineVoiceRecognizer()
        m_vr.start_listening()
        print("INFO: [Worker-Voice] Moonshine ASR engine listener active.")
    except Exception as e:
        print(f"WARNING: [Worker-Voice] Peripheral audio instance error: {e}")
        return

    while True:
        cmd_code = m_vr.get_keyword_command()
        if cmd_code is not None:
            h_mode.value = cmd_code
            if cmd_code == 0x01:
                is_tracking.value = 1
            elif cmd_code == 0x03:
                is_tracking.value = 0
        else:
            time.sleep(0.01)