import cv2
import time
import mediapipe as mp
from core.messenger import SerialMessenger
from core.face_yolo import FaceYOLO
from core.hand_mp import HandDetector

MODEL_PATH = "weights/best.pt"

def run_vision_loop():
    messenger = SerialMessenger('COM10', 115200)
    hand_det = HandDetector()
    face_det = FaceYOLO(MODEL_PATH)
    
    is_tracking_active = False 
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    prev_time = time.time()

    while True:
        success, frame = cap.read()
        if not success: break

        # --- 核心改进：无论是否在追踪，每帧都检测手势 ---
        h_mode, h_dx, h_dy, h_debug = hand_det.get_control_signal(frame)

        # 逻辑判断：手势拥有最高优先级的“切换权”
        if h_mode == 0x01: # 食指竖起 -> 强制开启人脸追踪
            if not is_tracking_active:
                is_tracking_active = True
                print(">>> 开启人脸追踪")
        elif h_mode == 0x03: # 剪刀手/其他设定手势 -> 强制关闭并归位
            if is_tracking_active:
                is_tracking_active = False
                print(">>> 关闭人脸追踪，回到手势模式")

        # --- 决策当前发送给串口的数据 ---
        if is_tracking_active:
            # 执行人脸追踪
            mode, dx, dy, debug_data = face_det.get_control_signal(frame)
            # 如果人脸跟丢了，我们不立即切回手势，保持追踪模式发送 mode 0x02 让云台停住
        else:
            # 执行手势控制（或者单纯待命）
            mode, dx, dy, debug_data = h_mode, h_dx, h_dy, h_debug

        # 发送协议
        messenger.send_target_offset(mode, dx, dy)

        # --- 绘制调试画面 (合并显示) ---
        # 1. 如果有手势，画手
        if h_debug:
            mp.solutions.drawing_utils.draw_landmarks(
                frame, h_debug, mp.solutions.hands.HAND_CONNECTIONS)
        
        # 2. 如果有人脸且在追踪，画框
        if is_tracking_active and debug_data and hasattr(debug_data, 'plot'):
            # 这里的 debug_data 是 face_det 返回的 results[0]
            # 为了不覆盖掉手部骨骼，我们直接在原图画框
            for box in debug_data.boxes:
                b = box.xyxy[0].cpu().numpy()
                cv2.rectangle(frame, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 255, 0), 2)

        # 状态显示
        fps = 1.0 / (time.time() - prev_time)
        prev_time = time.time()
        color = (0, 255, 0) if is_tracking_active else (0, 255, 255)
        cv2.putText(frame, f"FPS: {int(fps)} | ACTIVE: {is_tracking_active} | MODE: {hex(mode)}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.imshow("Gimbal Pro Control", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    messenger.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_vision_loop()