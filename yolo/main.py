import time
from multiprocessing import Process, Queue, Value
import cv2
import numpy as np
from core.control_filter import ControlFilter
from core.messenger import SerialMessenger
from core.pipeline_workers import run_face_tracking, run_hand_perception, run_voice_asr

MODEL_PATH = "weights/best.pt"


def main():

    is_tracking = Value('b', 0)
    h_mode = Value('B', 0x02)
    h_scale = Value('f', 50.0)
    out_dx = Value('i', 0)
    out_dy = Value('i', 0)

    hand_queue = Queue(maxsize=1)
    face_queue = Queue(maxsize=1)

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

    messenger = SerialMessenger('COM10', 115200)
    if messenger.ser is None or not messenger.ser.is_open:
        print("WARNING: Physical serial device missing. Running in simulation mode.")

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("ERROR: High-speed optical capture hardware connection failed.")
        messenger.close()
        return

    signal_filter = ControlFilter(alpha=0.25)
    last_scale = 50.0
    print("INFO: Master orchestrator pipeline running headless mode smoothly.")

    try:
        while True:
            success, frame = cap.read()
            if not success:
                break

            if hand_queue.empty():
                try: hand_queue.put_nowait(frame)
                except: pass
            if is_tracking.value == 1 and face_queue.empty():
                try: face_queue.put_nowait(frame)
                except: pass

            final_mode, render_dx, render_dy = signal_filter.process_signals(
                h_mode.value, h_scale.value, last_scale, 
                float(out_dx.value), float(out_dy.value)
            )
            last_scale = h_scale.value

            gain = float(np.clip(50.0 / max(h_scale.value, 10.0), 0.4, 2.2))

            if messenger.ser and messenger.ser.is_open:
                messenger.send_target_offset(
                    final_mode, int(render_dx * gain), int(render_dy * gain)
                )
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("INFO: Master orchestrator pipeline received manual interrupt code.")
    finally:
        for p in processes:
            p.terminate()
        cap.release()
        messenger.close()


if __name__ == "__main__":
    main()