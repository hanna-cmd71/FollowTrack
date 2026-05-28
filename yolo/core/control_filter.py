"""纯数值型信号时序平滑滤波器与跨模态自适应决策引擎模块。"""

import time


class ControlFilter:
    """管理离散控制模式判决树与物理运动量一阶低通时序滤波平滑的类。"""

    def __init__(self, alpha: float = 0.25):
        """初始化滤波平滑常数与内部时序计数器。

        Args:
            alpha: 低通滤波因子，范围在 0.0 到 1.0。数值越小，物理惯性越强。
        """
        self.alpha = alpha
        self.panic_timer = 0.0
        self.smooth_dx = 0.0
        self.smooth_dy = 0.0
        self.panic_active = False

    def process_signals(self, h_mode: int, current_scale: float,
                        last_scale: float, raw_dx: float,
                        raw_dy: float) -> tuple[int, int, int]:
        """对底层并轨采集的多路物理信号执行融合判决与低通指数平滑。

        Args:
            h_mode: 共享内存中锁定的离散行为控制代码。
            current_scale: 当前帧手掌空间相对绝对深度。
            last_scale: 上一帧手掌空间相对绝对深度。
            raw_dx: 视觉子进程运算产生的原始水平偏置量。
            raw_dy: 视觉子进程运算产生的原始垂直偏置量。

        Returns:
            Tuple[int, int, int]: 格式为 (最终决策控制码, 平滑后的 dx, 平滑后的 dy)。
        """
        current_time = time.time()

        # 应激突变判定：若检测到手掌空间深度在单帧内发生剧烈膨胀，激活应激状态
        if (current_scale - last_scale) > 40.0 and self.panic_timer == 0.0:
            self.panic_active = True
            self.panic_timer = current_time

        # 维护惊吓应激状态的时序自动收敛控制
        if self.panic_active:
            if current_time - self.panic_timer > 1.5:
                self.panic_active = False
                self.panic_timer = 0.0
                target_mode = 0x02
                target_dx, target_dy = 0.0, 0.0
            else:
                target_mode = 0x05  # 下位机对应的应激状态码
                target_dx, target_dy = 80.0, -30.0
        else:
            # 整合跨模态决策树行为映射
            if h_mode == 0x04:
                target_mode = 0x04  # 愉快字模代码
                target_dx, target_dy = raw_dx, raw_dy
            elif h_mode == 0x05:
                self.panic_active = True
                self.panic_timer = current_time
                target_mode = 0x05
                target_dx, target_dy = 80.0, -30.0
            elif h_mode == 0x01:
                # 若追踪状态下手掌距离过近，自动并轨映射为特殊近接互动模式
                target_mode = 0x04 if current_scale > 100.0 else 0x01
                target_dx, target_dy = raw_dx, raw_dy
            else:
                target_mode = h_mode
                target_dx, target_dy = 0.0, 0.0

        # 执行时序一阶低通滤波递推方程，滤除高频物理抖动
        self.smooth_dx = (self.alpha * target_dx + 
                          (1.0 - self.alpha) * self.smooth_dx)
        self.smooth_dy = (self.alpha * target_dy + 
                          (1.0 - self.alpha) * self.smooth_dy)

        return target_mode, int(self.smooth_dx), int(self.smooth_dy)