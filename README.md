# Multi-Modal Bionic Gimbal Interaction System (多模态仿生云台交互系统)

本项目是一个基于分布式多并发架构的智能仿生云台交互系统。系统集成了 YOLOv8 人脸动态追踪、MediaPipe 手势三维空间几何行为识别以及 vosk 边缘端离散语音流唤醒，通过跨模态决策树并轨融合算法，实现对下位机双轴舵机云台的时序平滑控制，并同步在 OLED 屏幕上渲染仿生拟人化表情。

---

## 系统架构总览

上位机系统采用 Python 多进程管道 (Multiprocessing) 确保边缘端高并发流吞吐效率，各感知子进程无阻塞异步解析特征，由主控制总线整合并下发指令。

* **`main.py`**：边缘交互控制路由器（核心总线），负责进程拉起、多路信号融合判决与串口分发。
* **`core/face_yolo.py`**：基于 YOLOv8 进行人脸目标偏差回归，并使用卡尔曼滤波器 (Kalman Filter) 实现时序状态估计，防止目标丢失跳变。
* **`core/hand_mp.py`**：基于 MediaPipe 提取手部拓扑空间几何特征，解析高级离散交互指令及相对物理深度。
* **`core/voice_asr.py`**：调用本地大模型环境进行上下文音频语义匹配，提取离散控制码。
* **`core/control_filter.py`**：整合跨模态判决树，并采用一阶低通指数平滑算法滤除传感器毛刺噪声。
* **`core/messenger.py`**：纯非阻塞瞬时分发串口协议层。

下位机

```mermaid
graph TD
    %% 样式定义
    classDef app fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef algo fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;
    classDef comm fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef hw fill:#fafafa,stroke:#212121,stroke-width:2px;

    %% 架构分层
    subgraph Layer1 [应用控制层 Application Layer]
        A["[gimbal_ctrl] 云台主状态机调度"]
        B["[OLED_Emotion] 智能仿生表情状态机"]
    end

    subgraph Layer2 [核心算法层 Algorithm Layer]
        C["[PID] 位置/增量式PID控制算法"]
        D["[Filter] 一阶低通滤波器 (Alpha=0.4)"]
    end

    subgraph Layer3 [协议与通信层 Communication Layer]
        E["[protocol] 上游视觉(YOLO)数据解析"]
        F["[vofa] VOFA+ 协议(JustFloat)"]
    end

    subgraph Layer4 [硬件驱动层 Hardware Driver Layer]
        G["[Servo] PWM 舵机角度及限幅控制"]
        H["[OLED] I2C SSD1306 显存安全驱动"]
    end

    %% 数据与控制流向
    E --> A
    A --> D
    D --> C
    C --> G
    A --> B
    B --> H
    C --> F

    %% 应用样式
    class A app;
    class B app;
    class C algo;
    class D algo;
    class E comm;
    class F comm;
    class G hw;
    class H hw;

---

## 环境依赖

### 1. 上位机环境 (Python 3.10+)

```bash
pip install opencv-python numpy pyserial ultralytics mediapipe sounddevice

# 创建模型目录
mkdir -p models
cd models

# 下载中文小模型（约42MB，速度快）
# 使用 PowerShell
Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip" -OutFile "vosk-model-small-cn-0.22.zip"

# 解压（使用Windows自带功能或安装7-Zip）
Expand-Archive -Path "vosk-model-small-cn-0.22.zip" -DestinationPath "."

# 重命名文件夹（去掉版本号）
Rename-Item "vosk-model-small-cn-0.22" "vosk-model-small-cn"

cd ..

```

### 2. 下位机环境 (MCU)

* 硬件：STM32F103 系列 / 兼容标准双轴 PWM 舵机驱动 / I2C 12864 OLED 屏幕
* 固件库：STM32CubeHAL (配置有 DMA 串口空闲中断接收与多路独立定时器 PWM)

---

## 通信协议规范

上位机与下位机采用严格的紧凑型结构体总线协议进行非阻塞瞬时分发，全长 7 字节：

| 字节偏移 | 数据类型 | 字段名 | 物理含义 | 备注 |
| --- | --- | --- | --- | --- |
| `0x00` | `uint8_t` | `header` | 帧固定包头 | 恒定为 `0x5A` |
| `0x01` | `int8_t` | `mode` | 系统行为模式码 | 参见下方模式映射 |
| `0x02~0x03` | `int16_t` | `x_offset` | X 轴物理像素偏差 (`dx`) | 小端序 (Little-Endian) |
| `0x04~0x05` | `int16_t` | `y_offset` | Y 轴物理像素偏差 (`dy`) | 小端序 (Little-Endian) |
| `0x06` | `uint8_t` | `tail` | 帧固定包尾 | 恒定为 `0xED` |

### 跨模态离散行为状态码

* `0x01 (MODE_TRACK)`：目标人脸追踪模式（OLED 渲染：动态聚焦眼）。
* `0x02 (MODE_LOCK)`：运动锁定原地看守模式（OLED 渲染：仿生眨眼）。
* `0x03 (MODE_HOME)`：云台回正低功耗休眠模式（OLED 渲染：闭眼横线）。
* `0x04 (MODE_HAPPY)`：愉快近接互动模式（OLED 渲染：月牙眯眼笑）。
* `0x05 (MODE_PANIC)`：突变量引发的惊吓应激模式（OLED 渲染：颤抖大惊失色眼）。

---

## 核心工程技术攻关点

### 1. 跨进程画布坐标系解耦对齐

在早期版本中，摄像头图像在被分发到不同检测器（YOLO 用 `320x320`，MediaPipe 用 `320x240`）时，由于直接提取了原始图像的大图中心点，导致坐标系尺度不一致。当前系统在 `FaceYOLO` 内部强制将输入帧等比例 resize 到网络推理分辨率，使计算偏差的中心点彻底稳定在 `(160, 160)` 归一化区间，消除了开局 `dx, dy` 瞬间打死饱和（卡死在 `-120, -90`）的隐患。

### 2. 卡尔曼滤波器冷启动保护

针对系统刚启动或目标丢失重获时，卡尔曼滤波器内部隐状态由于默认 `(0,0)` 导致预测值大幅度漂移的问题。系统加入了 `kf_initialized` 状态锁。在捕获到目标的第一帧，强行用真实观测值覆盖卡尔曼滤波器的状态矩阵，使其无需收敛时间即可平滑追踪。

### 3. 下位机超时应激闭眼保护

下位机固件 (`gimbal_ctrl.c`) 内部部署了独立的软件看门狗计时器。一旦上位机死机或断开连接导致串口数据中断超过 `TIMEOUT_THRESHOLD (50次计数)`，系统将自动切入保护模式，清除所有 PID 积分项、断开舵机能耗，并在 OLED 上显示闭眼，防止舵机持续堵转烧毁。

---

## 快速启动

1. 将下位机固件编译并烧录至 STM32 开发板。
2. 确认下位机串口连接至上位机，并在 `core/messenger.py` 中将 `port` 修改为对应的端口（如 `COM10` 或 `/dev/ttyUSB0`）。
3. 确认人脸检测权重文件已放置于 `weights/best.pt`。
4. 在终端执行主程序：

```bash
python main.py

```

---

## 许可证

本项目遵循 MIT 开源许可证。

---

*注：在实际运行中，可以通过按下键盘上的 'q' 键退出上位机可视化 debug 窗口。*
