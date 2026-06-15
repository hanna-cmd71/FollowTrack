import cv2
import numpy as np
try:
    import mediapipe.python.solutions.hands as mp_hands
except ImportError:
    from mediapipe.solutions import hands as mp_hands

from .base_detector import BaseDetector


class HandDetector(BaseDetector):
    """估计单手手势高级离散控制信号与相对空间物理深度的类。"""

    def __init__(self):
        """配置 MediaPipe 静态模型参数，优化轻量级边缘端前向吞吐率。"""
        self.mp_hands = mp_hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,  # 选择最轻量级的骨架跟踪拓扑网络
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )

    def get_control_signal(self, frame: np.ndarray) -> tuple[int, int, int, float]:
        """解析手部关键点拓扑空间几何关系，返回行为指令代码。"""
        if frame is None:
            return 0x02, 0, 0, 0.0

        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        # 若未检测到有效的关键点信息，返回无感知控制码
        if not results.multi_hand_landmarks:
            return 0x00, 0, 0, 0.0

        lms = results.multi_hand_landmarks[0].landmark

        # 提取 5 根手指的伸直状态（指尖节点 Y 轴高度低于第 2 关节）
        is_thumb_up = lms[4].x < lms[3].x if lms[17].x > lms[5].x else lms[4].x > lms[3].x # 拇指根据左右手简化判定
        is_index_up = lms[8].y < lms[6].y
        is_middle_up = lms[12].y < lms[10].y
        is_ring_up = lms[16].y < lms[14].y
        is_pinky_up = lms[20].y < lms[18].y

        # 计算大拇指至小拇指根部的欧氏几何像素距离作为景深距离因子
        p4 = np.array([lms[4].x * w, lms[4].y * h])
        p17 = np.array([lms[17].x * w, lms[17].y * h])
        hand_scale = float(np.linalg.norm(p4 - p17))

        # ==================== 【新规则手势决策树并轨映射】 ====================
        
        # 1. 食指单指竖起 -> 0x01 (TRACK 追踪)
        if is_index_up and not is_middle_up and not is_ring_up and not is_pinky_up:
            return 0x01, 0, 0, hand_scale
            
        # 2. 比耶手势 (食指 + 中指竖起) -> 0x04 (HAPPY 快乐笑脸)
        elif is_index_up and is_middle_up and not is_ring_up and not is_pinky_up:
            return 0x04, 0, 0, hand_scale
            
        # 3. 三根手指竖起 (食指 + 中指 + 无名指) -> 0x05 (PANIC 惊吓应激)
        elif is_index_up and is_middle_up and is_ring_up and not is_pinky_up:
            return 0x05, 0, 0, hand_scale
            
        # 4. 五指大张 (全竖起或除拇指外全竖起) -> 0x03 (HOME 回正休眠)
        elif is_index_up and is_middle_up and is_ring_up and is_pinky_up:
            return 0x03, 0, 0, hand_scale
            
        # 5. 其他模糊/过渡状态 -> 0x02 (LOCK 保持/锁定)
        else:
            return 0x02, 0, 0, hand_scale