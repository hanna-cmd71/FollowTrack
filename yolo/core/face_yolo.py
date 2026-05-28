"""基于 YOLOv8 的人脸目标偏差回归与卡尔曼时序状态估计模块。"""

import cv2
import numpy as np
from ultralytics import YOLO
from .base_detector import BaseDetector


class FaceYOLO(BaseDetector):
    """集成 CUDA 硬件加速推理与时序状态滤波预测的人脸目标追踪类。"""

    def __init__(self, model_path: str, conf: float = 0.6, imgsz: int = 320):
        """初始化深度神经网络模型与卡尔曼滤波器。

        Args:
            model_path: YOLOv8 训练完成的本地权重文件路径。
            conf: 目标检测置信度截断阈值。
            imgsz: 输入网络的目标网络分辨率。
        """
        self.model = YOLO(model_path)
        self.conf = conf
        self.imgsz = imgsz

        # 强制配置计算设备，启用首个可用的物理 GPU 核心进行加速
        self.device = 0

        # 初始化卡尔曼滤波器：包含 4 个状态量（x, y, dx, dy）和 2 个观测量（x, y）
        self.kf = cv2.KalmanFilter(4, 2)
        
        # 观测矩阵配置：系统仅可直接观测到目标的像素质心坐标 x 和 y
        self.kf.measurementMatrix = np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0]], np.float32
        )
        
        # 状态转移矩阵配置：下一时刻位置 = 当前位置 + 当前速度 * 采样周期
        self.kf.transitionMatrix = np.array(
            [[1, 0, 1, 0], 
             [0, 1, 0, 1], 
             [0, 0, 1, 0], 
             [0, 0, 0, 1]], np.float32
        )

        # 过程噪声与测量噪声协方差矩阵设定
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.01
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.1

        self.lost_count = 0
        self.MAX_LOST_FRAMES = 5  # 允许连续盲跟的最大时序跨度

    def get_control_signal(self, frame: np.ndarray) -> tuple[int, int, int, float]:
        """执行全流水线的目标检测、卡尔曼状态预测与边界回归。

        Args:
            frame: 当前相机捕获的原始图像。

        Returns:
            Tuple[int, int, int, float]: 格式为 (mode, dx, dy, target_width)。
        """
        if frame is None:
            return 0x02, 0, 0, 0.0

        h, w, _ = frame.shape
        center_x, center_y = w // 2, h // 2

        # 执行卡尔曼滤波的时序先验状态估计
        prediction = self.kf.predict()
        pred_x, pred_y = prediction[0][0], prediction[1][0]

        # 调度显卡核心执行卷积神经网络前向推理
        results = self.model.predict(
            source=frame,
            conf=self.conf,
            imgsz=self.imgsz,
            device=self.device,
            verbose=False,
        )

        # 解析模型预测边界框
        if results and len(results[0].boxes) > 0:
            self.lost_count = 0
            box = results[0].boxes.xywh[0].cpu().numpy()
            measured_x, measured_y = box[0], box[1]

            # 采用实际观测结果修正卡尔曼滤波器内部的隐状态变量
            self.kf.correct(
                np.array(
                    [[np.float32(measured_x)], [np.float32(measured_y)]],
                    dtype=np.float32,
                )
            )

            dx = int(measured_x - center_x)
            dy = int(measured_y - center_y)
            return 0x01, dx, dy, float(box[2])

        # 若当前帧目标丢失，进入基于先验物理速度的盲跟状态
        self.lost_count += 1
        if self.lost_count <= self.MAX_LOST_FRAMES:
            dx = int(pred_x - center_x)
            dy = int(pred_y - center_y)
            return 0x01, dx, dy, 0.0

        return 0x02, 0, 0, 0.0