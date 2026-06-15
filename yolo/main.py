import time
from multiprocessing import Process, Queue, Value
import cv2
import numpy as np
from core.control_filter import ControlFilter
from core.messenger import SerialMessenger
from core.pipeline_workers import run_face_tracking, run_hand_perception, run_voice_asr

MODEL_PATH = "weights/best.pt"


def main():
    # 多进程跨端状态共享总线
    is_tracking = Value('b', 0)
    h_mode = Value('B', 0x02)
    h_scale = Value('f', 50.0)
    out_dx = Value('i', 0)
    out_dy = Value('i', 0)

    # 跨进程有界非阻塞队列
    hand_queue = Queue(maxsize=1)
    face_queue = Queue(maxsize=1)

    # 并行计算集群调度
    processes = [
        Process(target=run_hand_perception, 
                args=(hand_queue, is_tracking, h_mode, h_scale), daemon=True),
        Process(target=run_face_tracking, 
                args=(face_queue, is_tracking, out_dx, out_dy, MODEL_PATH), 
                daemon=True),
        Process(target=run_voice_asr, 
                args=(is_tracking, h_mode), daemon=True)
    ]
    for p in processes:
        p.start()

    # 硬件串口物理链路初始化
    messenger = SerialMessenger('COM10', 115200)
    if messenger.ser is None or not messenger.ser.is_open:
        print("WARNING: Physical serial device missing. Running in simulation mode.")

    # 开启摄像头输入流
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("ERROR: Optical capture hardware connection failed.")
        messenger.close()
        return

    signal_filter = ControlFilter(alpha=0.25)
    last_scale = 50.0
    print("INFO: Master orchestrator pipeline running with GUI Debug Window.")

    # 初始化 OpenCV 
    cv2.namedWindow("Upper Monitor - Debug HUD", cv2.WINDOW_NORMAL)

    try:
        while True:
            success, frame = cap.read()
            if not success:
                break

            # 帧分发至子进程进行异步图像消费
            if hand_queue.empty():
                try: hand_queue.put_nowait(frame)
                except: pass
            if is_tracking.value == 1 and face_queue.empty():
                try: face_queue.put_nowait(frame)
                except: pass

            # 跨模态决策树并轨融合与平滑滤波
            final_mode, render_dx, render_dy = signal_filter.process_signals(
                h_mode.value, h_scale.value, last_scale, 
                float(out_dx.value), float(out_dy.value),
                h_mode_shared_ptr=h_mode
            )
            last_scale = h_scale.value

            gain = float(np.clip(50.0 / max(h_scale.value, 10.0), 0.4, 2.2))

            if messenger.ser and messenger.ser.is_open:
                messenger.send_target_offset(
                    final_mode, int(render_dx * gain), int(render_dy * gain)
                )

            debug_frame = frame.copy()
            h, w, _ = debug_frame.shape
            cx, cy = w // 2, h // 2

            cv2.line(debug_frame, (cx - 20, cy), (cx + 20, cy), (128, 128, 128), 1)
            cv2.line(debug_frame, (cx, cy - 20), (cx, cy + 20), (128, 128, 128), 1)
            
            target_px = int(cx + render_dx)
            target_py = int(cy + render_dy)
            cv2.circle(debug_frame, (target_px, target_py), 6, (0, 255, 0), -1)
            cv2.arrowedLine(debug_frame, (cx, cy), (target_px, target_py), (255, 0, 0), 2, tipLength=0.2)

            mode_map = {0x01: "TRACK", 0x02: "LOCK", 0x03: "HOME", 0x04: "HAPPY (Victory/Yeah)", 0x05: "PANIC (3 Fingers)"}
            mode_str = mode_map.get(final_mode, f"UNKNOWN ({hex(final_mode)})")

            hud_data = [
                f"SYS_MODE: {mode_str}",
                f"IS_TRACKING: {is_tracking.value}",
                f"RAW_OFFSET: dx={out_dx.value}, dy={out_dy.value}",
                f"FILT_OFFSET: dx={render_dx}, dy={render_dy}",
                f"HAND_SCALE: {h_scale.value:.1f} (Gain: {gain:.2f})"
            ]
            if final_mode == 0x05:
                hud_color = (0, 0, 255)      
            elif final_mode == 0x04:
                hud_color = (0, 255, 255)    
            else:
                hud_color = (0, 255, 0)      

            for i, text in enumerate(hud_data):
                cv2.putText(debug_frame, text, (15, 30 + i * 25), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, hud_color, 2, cv2.LINE_AA)

            cv2.imshow("Upper Monitor - Debug HUD", debug_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("INFO: Master orchestrator received manual 'q' interrupt.")
                break

    except KeyboardInterrupt:
        print("INFO: Master orchestrator received keyboard interrupt.")
    finally:
        for p in processes:
            p.terminate()
        cap.release()
        cv2.destroyAllWindows()
        messenger.close()


if __name__ == "__main__":
    main()