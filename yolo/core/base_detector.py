"""统一的底层视觉算法特征提取抽象基类。"""
    
from abc import ABC, abstractmethod
import numpy as np
"""
输入：
    frame: 输入帧数据
输出：
    dx, dy, mode, scale: 目标偏差，目标模式，目标缩放比例
"""
class BaseDetector(ABC):
    @abstractmethod
    def get_control_signal(self, frame: np.ndarray) -> tuple[int, int, int, float]:

        pass