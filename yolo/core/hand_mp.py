"""基于 MediaPipe 拓扑几何特征提取的手势离散行为识别模块。"""

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
            model_complexity=0,  # 强制选择最轻量级的骨架跟踪拓扑网络
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )

    def get_control_signal(self, frame: np.ndarray) -> tuple[int, int, int, float]:
        """解析手部关键点拓扑空间几何关系，返回行为指令代码。

        Args:
            frame: 用于进行手势识别的图像输入。

        Returns:
            Tuple[int, int, int, float]: 格式为 (mode, dx, dy, hand_scale)。
                mode 说明: 0x01为追踪, 0x03为回正休眠, 0x02为模糊手势, 0x00为无感知。
        """
        if frame is None:
            return 0x02, 0, 0, 0.0

        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        # 若未检测到有效的关键点信息，返回无感知控制码
        if not results.multi_hand_landmarks:
            return 0x00, 0, 0, 0.0

        lms = results.multi_hand_landmarks[0].landmark

        # 提取核心手指的伸直状态（依据指尖节点与第2关节在 Y 轴的相对高度）
        is_index_up = lms[8].y < lms[6].y
        is_middle_up = lms[12].y < lms[10].y
        is_ring_up = lms[16].y < lms[14].y
        is_pinky_up = lms[20].y < lms[18].y

        # 计算大拇指基部（4号点）到小指基部（17号点）的欧氏像素距离作为空间深度因子
        p4 = np.array([lms[4].x * w, lms[4].y * h])
        p17 = np.array([lms[17].x * w, lms[17].y * h])
        hand_scale = float(np.linalg.norm(p4 - p17))

        # 基于几何边界判定的离散有限状态机行为树
        if is_index_up and not is_middle_up and not is_ring_up and not is_pinky_up:
            return 0x01, 0, 0, hand_scale  # 仅竖起食指：触发召唤激活指令
        elif is_index_up and is_middle_up and is_ring_up and is_pinky_up:
            return 0x03, 0, 0, hand_scale  # 五指大张：触发归位休眠指令
        else:
            return 0x02, 0, 0, hand_scale  # 中间过渡状态或无法匹配的模糊手势