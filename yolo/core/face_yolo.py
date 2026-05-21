import numpy as np
import cv2
from .base_detector import BaseDetector
from ultralytics import YOLO

class FaceYOLO(BaseDetector):
    def __init__(self, model_path, conf=0.6, imgsz=320):
        self.model = YOLO(model_path)
        self.conf = conf
        self.imgsz = imgsz
        
        # --- 初始化卡尔曼滤波器 ---
        # 状态量: [x, y, dx, dy] (中心坐标, 速度)
        self.kf = cv2.KalmanFilter(4, 2)
        # 观测矩阵: 我们只能观测到 x, y
        self.kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
        # 状态转移矩阵: 下一秒的位置 = 当前位置 + 速度*1
        self.kf.transitionMatrix = np.array([[1, 0, 1, 0], 
                                             [0, 1, 0, 1], 
                                             [0, 0, 1, 0], 
                                             [0, 0, 0, 1]], np.float32)
        
        # 噪声参数（论文里可以作为对比实验的变量）
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.01 
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.1
        
        self.lost_count = 0  # 连续丢失帧数计数
        self.MAX_LOST = 5   # 最大允许盲跟帧数（约0.3-0.5秒）

    def get_control_signal(self, frame):
        h, w, _ = frame.shape
        center_x, center_y = w // 2, h // 2
        
        # 1. 滤波器首先进行“先验预测”
        prediction = self.kf.predict()
        pred_x, pred_y = prediction[0][0], prediction[1][0]

        # 2. YOLO 执行检测（观测）
        results = self.model.predict(source=frame, conf=self.conf, imgsz=self.imgsz, device=0, verbose=False)
        
        if results and len(results[0].boxes) > 0:
            # --- 观测到目标：进行“修正” ---
            self.lost_count = 0
            box = results[0].boxes.xywh[0].cpu().numpy()
            measured_x, measured_y = box[0], box[1]
            
            # 使用 YOLO 结果修正滤波器状态
            self.kf.correct(np.array([[np.float32(measured_x)], [np.float32(measured_y)]]))
            
            dx = int(measured_x - center_x)
            dy = int(measured_y - center_y)
            return 0x01, dx, dy, results[0]
            
        else:
            # --- 目标丢失：进入“盲跟/预测”模式 ---
            self.lost_count += 1
            
            if self.lost_count < self.MAX_LOST:
                # 关键改进：使用滤波器的预测值作为输出，让云台继续转动
                dx = int(pred_x - center_x)
                dy = int(pred_y - center_y)
                
                # 即使没看到人，我们也发 0x01 (持续追踪)，但返回 None 作为调试数据
                # 这里的模式可以自定义，比如 0x04 代表“预测追踪”
                return 0x01, dx, dy, None 
            
            # 彻底丢失目标
            return 0x02, 0, 0, None