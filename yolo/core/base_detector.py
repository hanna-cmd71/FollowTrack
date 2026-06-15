from abc import ABC, abstractmethod
import numpy as np

class BaseDetector(ABC):
    """统一的底层视觉算法特征提取抽象基类。"""
    
    @abstractmethod
    def get_control_signal(self, frame: np.ndarray) -> tuple[int, int, int, float]:
        """输入帧数据，解算并输出目标偏差、目标模式以及尺寸缩放比例系数。"""
        pass