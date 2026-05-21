from abc import ABC, abstractmethod
import numpy as np

class BaseDetector(ABC):
    @abstractmethod
    def get_control_signal(self, frame: np.ndarray):
        """返回格式: (mode, dx, dy, debug_data)"""
        pass