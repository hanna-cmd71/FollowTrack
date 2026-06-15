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
                        raw_dy: float, h_mode_shared_ptr=None) -> tuple[int, int, int]:
        """对底层并轨采集的多路物理信号执行融合判决与低通指数平滑。"""
        current_time = time.time()
        target_mode = h_mode
        target_dx, target_dy = raw_dx, raw_dy

        # 1. 雷达测距突变量检测：如果手掌相对上一帧迅速逼近超过安全阈值，强制切入 Panic 惊吓
        if last_scale > 10.0 and (current_scale - last_scale) > 45.0 and not self.panic_active:
            self.panic_active = True
            self.panic_timer = current_time

        # 2. 从多进程事件总线捕获到 0x05，激活定时管控状态机
        if h_mode == 0x05 and not self.panic_active:
            self.panic_active = True
            self.panic_timer = current_time

        # 3. 维护惊吓应激状态的时序自动收敛控制
        if self.panic_active:
            if current_time - self.panic_timer > 1.5:
                # 1.5秒应激时效届满，解除惊吓状态，平稳归位收敛
                self.panic_active = False
                self.panic_timer = 0.0
                target_mode = 0x02  # 自动重置降级为 MODE_LOCK
                target_dx, target_dy = 0.0, 0.0
                
                # 【核心闭环】：必须反向擦除共享内存状态，否则会陷入惊吓死循环
                if h_mode_shared_ptr is not None:
                    h_mode_shared_ptr.value = 0x02
            else:
                target_mode = 0x05  # 维持下位机 Panic 惊吓指令
                target_dx, target_dy = 40.0, 20.0  # 固定的躲避突跳动作
        else:
            # 4. 正常非惊吓状态下的业务映射
            if h_mode == 0x04:
                target_mode = 0x04  
                target_dx, target_dy = raw_dx, raw_dy
            elif h_mode == 0x01:
                # 如果手离得极近，自动在追踪中展示开心表情
                target_mode = 0x04 if current_scale > 100.0 else 0x01
                target_dx, target_dy = raw_dx, raw_dy

        # 一阶低通时序滤波平滑
        self.smooth_dx = self.alpha * target_dx + (1.0 - self.alpha) * self.smooth_dx
        self.smooth_dy = self.alpha * target_dy + (1.0 - self.alpha) * self.smooth_dy

        # 边界幅值截断限幅
        final_dx = int(max(min(self.smooth_dx, 320), -320))
        final_dy = int(max(min(self.smooth_dy, 240), -240))

        return target_mode, final_dx, final_dy