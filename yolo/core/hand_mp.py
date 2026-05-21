import cv2
# 终极绕过方案：直接从底层 sub-package 导入
try:
    import mediapipe.python.solutions.hands as mp_hands
    import mediapipe.python.solutions.drawing_utils as mp_drawing
except ImportError:
    # 兼容某些版本可能存在的路径差异
    from mediapipe.solutions import hands as mp_hands
    from mediapipe.solutions import drawing_utils as mp_drawing

from .base_detector import BaseDetector

class HandDetector(BaseDetector):
    def __init__(self):
        # 放弃使用 mp.solutions，直接绑定导入的模块
        self.mp_hands = mp_hands
        self.mp_draw = mp_drawing
        
        # 这里的实例化不依赖于 mediapipe 顶层对象的属性
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,  # 0最快
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def get_control_signal(self, frame):
        if frame is None:
            return 0x02, 0, 0, None
            
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        if not results.multi_hand_landmarks:
            return 0x02, 0, 0, None

        lms = results.multi_hand_landmarks[0].landmark
        
        # 手势逻辑：8-食指尖, 6-食指关节; 12-中指尖, 10-中指关节
        is_index_up = lms[8].y < lms[6].y
        is_middle_up = lms[12].y < lms[10].y

        if is_index_up and not is_middle_up:
            mode = 0x01 # 追踪
            dx = int(lms[8].x * w - w // 2)
            dy = int(lms[8].y * h - h // 2)
        elif is_index_up and is_middle_up:
            mode = 0x03 # 归位
            dx, dy = 0, 0
        else:
            mode = 0x02 # 锁定
            dx, dy = 0, 0

        return mode, dx, dy, results.multi_hand_landmarks[0]