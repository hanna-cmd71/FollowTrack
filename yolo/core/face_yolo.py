import cv2
import numpy as np
from ultralytics import YOLO
from .base_detector import BaseDetector

class FaceYOLO(BaseDetector):
    def __init__(self, model_path: str, conf: float = 0.5, imgsz: int = 320): # 调低conf增强鲁棒性
        self.model = YOLO(model_path)
        self.conf = conf
        self.imgsz = imgsz
        self.device = 0

        self.kf = cv2.KalmanFilter(4, 2)
        self.kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float32)
        
        # 【调参】：适当增大过程噪声，允许模型应对更剧烈的运动
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03 
        # 【调参】：稍微减小测量噪声，让滤波器更相信 YOLO 的识别结果
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.05
        
        self.kf.errorCovPost = np.eye(4, dtype=np.float32) * 1.0
        self.lost_count = 0
        self.is_initialized = False # 新增：标识KF是否已建立有效状态

    def _reset_kf(self, x, y):
        """当发生长时间丢失后，重置卡尔曼状态，防止旧状态干扰"""
        self.kf.statePost = np.array([[x], [y], [0], [0]], dtype=np.float32)
        self.kf.errorCovPost = np.eye(4, dtype=np.float32) * 1.0
        self.is_initialized = True

    def get_control_signal(self, frame: np.ndarray) -> tuple[int, int, int, float]:
        if frame is None: return 0x02, 0, 0, 0.0
        h, w, _ = frame.shape
        center_x, center_y = w // 2, h // 2

        prediction = self.kf.predict()
        pred_x, pred_y = prediction[0][0], prediction[1][0]

        results = self.model.predict(
            source=frame, conf=self.conf, imgsz=self.imgsz, device=self.device, verbose=False
        )

        if results and len(results[0].boxes) > 0:
            box = results[0].boxes.xywh[0].cpu().numpy()
            measured_x, measured_y = box[0], box[1]

            # 逻辑优化：如果是刚恢复追踪或者长时间丢失后找回，强制重置KF
            if self.lost_count > 5 or not self.is_initialized:
                self._reset_kf(measured_x, measured_y)
            
            self.kf.correct(np.array([[np.float32(measured_x)], [np.float32(measured_y)]], dtype=np.float32))
            self.lost_count = 0 # 找回目标，重置计数

            return 0x01, int(measured_x - center_x), int(measured_y - center_y), float(box[2])
        else:
            self.lost_count += 1
            # 逻辑优化：将阈值从 10 扩大到 30 (约 1 秒)，允许短时间遮挡
            if self.lost_count < 30: 
                # 依然返回 0x01，通过 KF 预测值进行“盲追”，防止云台立刻停止
                return 0x01, int(pred_x - center_x), int(pred_y - center_y), 0.0
            else:
                self.is_initialized = False # 彻底丢失，标记为未初始化
                return 0x02, 0, 0, 0.0