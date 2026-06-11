import time

class ControlFilter:
    """管理离散控制模式判决树与物理运动量一阶低通时序滤波平滑的类。"""

    def __init__(self, alpha: float = 0.25):
        self.alpha = alpha
        self.panic_timer = 0.0
        self.smooth_dx = 0.0
        self.smooth_dy = 0.0
        self.panic_active = False

    def process_signals(self, h_mode: int, current_scale: float,
                        last_scale: float, raw_dx: float,
                        raw_dy: float) -> tuple[int, int, int]:
        """对底层并轨采集的多路物理信号执行融合判决与低通指数平滑。"""
        current_time = time.time()
        target_mode = h_mode
        target_dx, target_dy = raw_dx, raw_dy

        # 突变量检测：如果手掌相对上一帧迅速逼近超过安全阈值，强制切入 Panic 惊吓
        if last_scale > 10.0 and (current_scale - last_scale) > 45.0 and not self.panic_active:
            self.panic_active = True
            self.panic_timer = current_time

        # 维护惊吓应激状态的时序自动收敛控制
        if self.panic_active:
            if current_time - self.panic_timer > 1.5:
                self.panic_active = False
                self.panic_timer = 0.0
                target_mode = 0x02  # 恢复 MODE_LOCK
                target_dx, target_dy = 0.0, 0.0
            else:
                target_mode = 0x05  # 触发下位机 Panic 惊吓大眼
                # 惊吓动作：给云台一个可控的突跳正向偏置，不再输入负数防撞墙
                target_dx, target_dy = 40.0, 20.0
        else:
            # 整合跨模态决策树行为映射
            if h_mode == 0x04:
                target_mode = 0x04  
                target_dx, target_dy = raw_dx, raw_dy
            elif h_mode == 0x05:
                self.panic_active = True
                self.panic_timer = current_time
                target_mode = 0x05
                target_dx, target_dy = 40.0, 20.0
            elif h_mode == 0x01:
                
                target_mode = 0x04 if current_scale > 100.0 else 0x01
                target_dx, target_dy = raw_dx, raw_dy

        self.smooth_dx = self.alpha * target_dx + (1.0 - self.alpha) * self.smooth_dx
        self.smooth_dy = self.alpha * target_dy + (1.0 - self.alpha) * self.smooth_dy

     
        final_dx = int(max(min(self.smooth_dx, 320), -320))
        final_dy = int(max(min(self.smooth_dy, 240), -240))

        return target_mode, final_dx, final_dy