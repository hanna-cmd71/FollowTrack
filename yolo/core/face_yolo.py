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
            [[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float32
        )

        # ====== 【核心修复点】：修正 OpenCV Python 绑定的属性命名，去掉 ❌ covariance 后缀 ======
        # 1. 过程噪声协方差矩阵（允许目标速度快速切换）
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 1e-2 

        # 2. 测量噪声协方差矩阵（抗传感器高频抖动）
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1e-1

        # 3. 后验错误协方差矩阵（初始状态置信度评估）
        self.kf.errorCovPost = np.eye(4, dtype=np.float32) * 1.0
        # ===================================================================================

        # 目标丢失计数器，用于丢失目标后的平滑衰减
        self.lost_count = 0

    def get_control_signal(self, frame: np.ndarray) -> tuple[int, int, int, float]:
        """调度物理相机捕获的原始图像。

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
                    dtype=np.float32
                )
            )

            # 计算人脸中心相对画面中心的物理像素偏差量
            dx = int(measured_x - center_x)
            dy = int(measured_y - center_y)
            target_width = float(box[2])

            return 0x01, dx, dy, target_width

        else:
            # 目标丢失状态处理机制
            self.lost_count += 1
            
            if self.lost_count < 10:
                # 10帧以内采用卡尔曼先验预测值维持盲追，防止高频瞬时丢包导致的云台剧烈顿挫
                dx = int(pred_x - center_x)
                dy = int(pred_y - center_y)
                return 0x01, dx, dy, 0.0
            else:
                # 超过10帧彻底判定目标丢失，进入回中或平稳锁定模式
                return 0x02, 0, 0, 0.0