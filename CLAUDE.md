# 通信系统综合设计与实践 — 微型无中心自组网络设计

## 课程信息

- **课程**：通信系统综合设计与实践
- **学院**：微电子与通信工程
- **年级**：2023级
- **课题**：微型无中心自组网络设计
- **周期**：2026.6.22 ~ 2026.7.10（三周）
- **分组**：4人一组，分工合作，每人必须含程序编写
- **评分**：过程20% | 方案20% | 结果30% | 报告30%

## 设计目标

1. 掌握 Arduino 开发，完成无线传输设备
2. 理解无线网络原理，完成微型低速无线网络系统
3. 团队分工合作

## 基本要求

1. **3个节点**无线通信系统，各节点**地位平等**，均可启动组网
2. 节点间**两两相互通信**，可**正常退网**
3. PC端基于 **LabVIEW** 设计可视化控制界面
4. 统一**自定义通信协议**
5. 绘制**结构化程序详细设计图**（N-S图、状态转换图等）

## 提高要求

1. 实现第4个节点加入
2. 支持**广播**、**非正常退网**、**网络状态实时显示**
3. 可测试网络通信参数（可靠性/稳定性）
4. 完整组网设计方案（状态转换图、软件模块设计、伪代码）
5. 扩展发挥，设计实用环境

## 硬件平台

| 硬件 | 说明 |
|------|------|
| 控制板 | PlayKit（兼容Arduino，UNO模式：开关7/8/9拨到ON） |
| LoRa模块 | Ra-02（SX1278芯片），SPI接口，半双工 |
| ISM频段 | 410–525MHz |
| 模块供电 | 3.3V，峰值电流200mA以上 |
| 灵敏度 | -140dBm ~ -148dBm |
| 发射功率 | 最大+20dBm |
| 天线形式 | IPEX座子 |
| SPI引脚 | D10(SS)、D11(MOSI)、D12(MISO)、D13(SCK) |
| 片选(CS) | 连接到 **A3** 引脚，代码需设 `LoRa.setPins(A3)` |
| LoRa库 | 已解压于 `1.LoRa资料/LoRa库文件/arduino-LoRa-master/`，复制到 Arduino libraries 即可使用 |

### Ra-02 模块引脚定义（SX1278）

| 脚序 | 名称 | 功能说明 |
|------|------|----------|
| 测试点 | ANT | 接天线 |
| 1,2,9,16 | GND | 接地 |
| 3 | 3.3V | 供电（典型值3.3V） |
| 4 | RESET | 复位脚 |
| 5 | DIO0 | 数字IO，软件配置（中断用，默认D2） |
| 6 | DIO1 | 数字IO，软件配置 |
| 7 | DIO2 | 数字IO，软件配置 |
| 8 | DIO3 | 数字IO，软件配置 |
| 10 | DIO4 | 数字IO，软件配置 |
| 11 | DIO5 | 数字IO，软件配置 |
| 12 | SCK | SPI时钟输入 |
| 13 | MISO | SPI数据输出 |
| 14 | MOSI | SPI数据输入 |
| 15 | NSS | SPI片选输入（连接到A3） |

## 完整目录树

```
E:/arduino_design/
├── CLAUDE.md                               # ← 本文件
│
└── 说明文档/
    ├── 实验任务.docx                       # 课程任务书
    ├── 实验内容说明.pptx                   # 实验内容PPT
    ├── Lora 信道分配.docx                  # 信道分配方案
    ├── 串口猎人(Serial Hunter) V31 setup.exe
    │
    └── 通信系统综合设计与实践资料下发/
        │
        ├── Mega2560 REV3引脚.pdf           # Mega2560 引脚图
        ├── Uno REV3引脚.pdf                # Uno 引脚图
        │
        ├── 1.LoRa资料/
        │   ├── Ra-02产品规格书.pdf          # 安信可Ra-02(SX1278)规格书
        │   ├── Ra-01模块的LoRa板片选管脚说明.docx
        │   ├── LoRa库API.docx             # LoRa库API手册
        │   │
        │   ├── LoRa库文件/
        │   │   ├── arduino-LoRa-master.rar
        │   │   └── arduino-LoRa-master/   # 已解压
        │   │       └── arduino-LoRa-master/
        │   │           ├── API.md
        │   │           ├── README.md
        │   │           ├── LICENSE
        │   │           ├── .travis.yml
        │   │           ├── issue_template.md
        │   │           ├── keywords.txt
        │   │           ├── library.properties
        │   │           ├── src/
        │   │           │   ├── LoRa.h
        │   │           │   └── LoRa.cpp
        │   │           └── examples/
        │   │               ├── LoRaSender/             # 基础发送
        │   │               │   └── LoRaSender.ino
        │   │               ├── LoRaReceiver/           # 基础接收
        │   │               │   └── LoRaReceiver.ino
        │   │               ├── LoRaReceiverCallback/   # 回调式接收
        │   │               │   └── LoRaReceiverCallback.ino
        │   │               ├── LoRaDuplex/             # 半双工通信
        │   │               │   └── LoRaDuplex.ino
        │   │               ├── LoRaDuplexCallback/     # 回调式半双工
        │   │               │   └── LoRaDuplexCallback.ino
        │   │               ├── LoRaSenderNonBlocking/  # 非阻塞发送
        │   │               │   └── LoRaSenderNonBlocking.ino
        │   │               ├── LoRaSenderNonBlockingCallback/
        │   │               │   └── LoRaSenderNonBlockingCallback.ino
        │   │               ├── LoRaSetSpread/          # 设置扩频因子
        │   │               │   └── LoRaSetSpread.ino
        │   │               ├── LoRaSetSyncWord/        # 设置同步字
        │   │               │   └── LoRaSetSyncWord.ino
        │   │               ├── LoRaDumpRegisters/      # 寄存器转储
        │   │               │   └── LoRaDumpRegisters.ino
        │   │               ├── LoRaSimpleGateway/      # 简单网关
        │   │               │   └── LoRaSimpleGateway.ino
        │   │               └── LoRaSimpleNode/         # 简单节点
        │   │                   └── LoRaSimpleNode.ino
        │   │
        │   └── LoRa实验/
        │       ├── LoRa实验.docx           # 实验指导书
        │       ├── 实验1/                  # LoRa一收一发串口通信
        │       │   ├── LoRaSender/
        │       │   │   └── LoRaSender.ino
        │       │   └── LoRaReceiver/
        │       │       └── LoRaReceiver.ino
        │       └── 实验2/                  # LoRa双向串口通信(半双工)
        │           ├── LoRaSender1/
        │           │   └── LoRaSender1.ino
        │           └── LoRaReceiver/
        │               └── LoRaReceiver.ino
        │
        └── 2.LaLabVIEW串口通信/
            ├── Labview串口通信实验.docx     # LabVIEW实验指导书
            ├── Typical_serial_read and write.vi
            ├── LabVIEW控制Arduino板载LED灯/
            │   ├── LabVIEW_serial_write.vi
            │   └── Uno_serial_read/
            │       └── Uno_serial_read.ino
            └── LabVIEW采集Arduino模拟值/
                ├── LabVIEW_serial_read.vi
                └── Uno_serial_write/
                    └── Uno_serial_write.ino
```

## LoRa API 速查

```cpp
#include <SPI.h>
#include <LoRa.h>

LoRa.begin(frequency);         // 初始化，如 433E6
LoRa.setPins(ss, reset, dio0); // 重设引脚（片选/复位/DIO0）
LoRa.setSPIFrequency(freq);    // 设置SPI频率，默认10MHz
LoRa.beginPacket();            // 开始发送包
LoRa.print(data);              // 写入数据
LoRa.endPacket();              // 结束发送
LoRa.parsePacket();            // 检查是否有接收数据
LoRa.read();                   // 读取接收字节
LoRa.packetRssi();             // 获取信号强度
LoRa.available();              // 缓冲区剩余字符数
```

## LoRa 信道分配

待分组确定后按以下方案分配（每8M间隔细分3-4信道）：

| 组号 | 频段 | 扩频因子 | 组号 | 频段 | 扩频因子 |
|------|------|----------|------|------|----------|
| 1组 | 410-417 MHz | 6bit | 6组 | 428-435 MHz | 7bit |
| 2组 | 418-427 MHz | 6bit | 7组 | 410-416 MHz | 8bit |
| 3组 | 428-435 MHz | 6bit | 8组 | 417-423 MHz | 8bit |
| 4组 | 410-417 MHz | 7bit | 9组 | 424-430 MHz | 8bit |
| 5组 | 418-427 MHz | 7bit | 10组 | 431-437 MHz | 8bit |

> **当前分组：7组** → 使用 **410–416 MHz**，**8bit 扩频因子**。代码中写入 `LoRa.begin(413E6)`（取中间频段 413MHz）。

## 自定义通信协议

### 物理层
- 频率 413MHz（7组），扩频因子 8，同步字 0xcd，硬件 CRC

### 帧结构
```
| DAddr(1) | SAddr(1) | Function(1) | DataLen(1) | MCS(1) | MsgData(N) |
```

### 地址
| 地址 | 含义 |
|------|------|
| ASCII '0' | 未分配（新节点） |
| ASCII '1'~'4' | 节点地址，最多 4 个 |
| ASCII 'A' | 广播地址 |

### 功能码
| 码 | 方向 | 含义 |
|----|------|------|
| `J` | 新→网内 | 申请入网 |
| `j` | 网内→新 | 同意入网 + 分配地址 |
| `H` | 全网广播 | 心跳，携带本机路由表 |
| `L` | 退网→广播 | 通知退网 |
| `l` | 收→退 | 退网确认 |
| `D` | 任意→任意 | 单播数据 |
| `d` | 收→发 | 数据确认 |
| `B` | 任意→广播 | 广播数据 |

### 心跳与路由表
心跳数据携带 4 位路由状态（如 `"1011"` 表示地址1在线、地址2离线、地址3/4在线），所有节点收到后**直接+间接**学习全网节点状态。12 秒无心跳判离线。

### 入网流程
```
新节点扫描 3~7s → 听到心跳 → 发 J 给目标 → 收到 j（含地址）→ 入网 → 快速广播 5 次心跳
超时3次 → 回退到扫描
首个节点：扫描后无回复，自分配地址 '1'
```

### 校验
`MCS = DAddr ^ SAddr ^ Function ^ DataLen`（XOR）

### 串口命令（PC→板子）
| 命令 | 格式 | 含义 |
|------|------|------|
| `S` | 仅字符 | 打印路由表 |
| `D<addr><data>` | `D2Hello` | 单播到指定节点 |
| `B<data>` | `BHello All` | 广播数据 |
| `L` | 仅字符 | 退网 |

## LoRa 实验代码参考

### 实验1：LoRa一收一发

**发送端**（LoRaSender.ino）：
```cpp
void loop() {
  Serial.print("Sending packet: ");
  Serial.println(counter);
  LoRa.beginPacket();
  LoRa.print("hello ");
  LoRa.print(counter);
  LoRa.endPacket();
  counter++;
  delay(5000);
}
```

**接收端**（LoRaReceiver.ino）：
```cpp
void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    Serial.print("Received packet '");
    for (int i = 0; i < packetSize; i++)
      Serial.print((char)LoRa.read());
    Serial.print("' with RSSI ");
    Serial.println(LoRa.packetRssi());
  }
}
```

### 实验2：LoRa双向串口通信（半双工）

串口输入 → LoRa发送；同时 LoRa接收 → 串口打印：
```cpp
void loop() {
  // 串口输入 → LoRa发送
  char val = Serial.read();
  if (-1 != val) {
    Serial.print(val);
    LoRa.beginPacket();
    LoRa.print(val);
    LoRa.endPacket();
  }
  // LoRa接收 → 串口打印
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    while (LoRa.available())
      Serial.print((char)LoRa.read());
  }
}
```

## PySide6 监控上位机

替代 LabVIEW，使用 Python PySide6 实现串口监控面板。位于 `proj/main/gui/serial_monitor.py`。

### 启动方式

```bash
python proj/main/gui/serial_monitor.py
```

### 界面布局

```
┌───────────────────────────────────────────────────────────┐
│  路由表                           │  网络统计              │
│  节点A: Node 1                    │  TX packets: 5        │
│  节点B: Node 2                    │  RX packets: 3        │
│  节点C: Node 4                    │  RSSI: -45 dBm        │
└───────────────────────────────────────────────────────────┘
┌──────────┬──────────┬──────────┬──────────────────────────┐
│  节点A   │  节点B    │  节点C   │  节点D                   │
│ [COM7][连]│ [COM6][连]│ [COM9][断]│ [COM12][连]             │
│ [命令][发]│ [命令][发]│ [命令][发]│ [命令][发]              │
│ 日志框    │ 日志框    │ 日志框    │ 日志框                  │
└──────────┴──────────┴──────────┴──────────────────────────┘
```

### 功能特点
- 四个独立串口面板，支持 4 个节点同时监控
- 自动扫描本机真实 COM 口，不显示虚拟串口
- 连接后自动识别节点地址，标题改为 `节点A - Node 2` 格式
- 路由表实时更新（只显示在线节点，不叠加）
- 网络统计按 key 覆盖更新（不堆积旧值）
- 内置 DTR 控制，避免 Arduino UNO 连接时自动复位

## LabVIEW 串口通信

- 使用 **VISA** 插件实现串口编程（需提前安装 NI-VISA 驱动）
- 典型流程：VISA配置串口（串口号/波特率 9600/数据位8/停止位1/无校验）→ VISA读写 → VISA关闭
- 通信协议：自定义帧头 + 数据内容

### Arduino端代码参考

**LED控制**（Uno_serial_read.ino，LabVIEW→Arduino）：
```cpp
void loop() {
  if (Serial.available() > 0) {
    byte comdata = Serial.read();
    if (comdata == 0x01) digitalWrite(13, LOW);  // 关灯
    if (comdata == 0x02) digitalWrite(13, HIGH); // 开灯
  }
}
```

**模拟值上传**（Uno_serial_write.ino，Arduino→LabVIEW）：
```cpp
void loop() {
  int sensorValue = analogRead(A0);
  float voltage = (float)sensorValue / 1023 * 5.00;
  Serial.print("66");                   // 帧头标记有效帧
  Serial.print(voltage, 2);            // 保留两位小数
  delay(1000);
}
```

## 设计任务时间线

1. **第一周**（6.22–6.28）：掌握 Arduino 开发原理，完成无线设备基本设计，完成网络系统设计方案
2. **第二周**（6.29–7.5）：完成各通信模块设计测试，完成基本组网设计
3. **第三周**（7.6–7.10）：整体系统程序编写与测试，完成报告编写

## 开发工作区

- **项目代码目录**：`E:\arduino_design\proj\`（所有编写/修改的 .ino 等代码文件都在此目录下进行）
- **文档查阅**：`E:\arduino_design\说明文档\`（原始文档和 `parsed_*` 解析结果，以及参考ino代码均在此，需要时查阅，不在该目录下写代码）

## 本机开发环境

| 工具 | 路径 |
|------|------|
| Arduino IDE | `E:\arduino-1.8.19\` |
| arduino-cli | `E:\Arduino CLI\arduino-cli.exe`，已加入环境变量 |
| LoRa库 | 已解压于 `说明文档/通信系统综合设计与实践资料下发/1.LoRa资料/LoRa库文件/arduino-LoRa-master/`，复制到 Arduino libraries 即可使用 |
| 串口调试 | `说明文档/串口猎人(Serial Hunter) V31 setup.exe` — 第三方串口调试助手，支持多串口监控、HEX/ASCII显示、波形查看等功能，比 arduino-cli monitor 功能更强 |
| 板子（大板） | PlayKit，ATmega328P，UNO模式，port COM12 |
| 板子（小板） | Arduino UNO R3，ATmega328P，port COM6/COM7/COM9 |
| 虚拟串口 | 已改到 COM20↔COM21，释放 COM6/COM7 |

### arduino-cli 常用命令

```bash
# 列出已连接的开发板端口
arduino-cli board list

# 编译
arduino-cli compile --fqbn arduino:avr:uno <sketch目录>

# 上传（因 avrdude 8.0 配置文件有 bug，改用 IDE 自带的 avrdude 6.3）
arduino-cli compile --fqbn arduino:avr:uno --output-dir <sketch目录>/build <sketch目录>
"E:/arduino-1.8.19/hardware/tools/avr/bin/avrdude" -C"E:/arduino-1.8.19/hardware/tools/avr/etc/avrdude.conf" -v -patmega328p -carduino -P<端口号> -b115200 -D -Uflash:w:<sketch目录>/build/<sketch>.ino.hex:i

# 串口监视器（类似 Arduino IDE 串口监视器，基础功能）
arduino-cli monitor --port <端口号> --config baudrate=9600
```

### 串口监听脚本

`proj/tools/serial_listener.py` — 后台串口监听脚本，已内置 `ser.setDTR(False)` 防止 Arduino UNO 自动复位，可用于调试时实时获取板子串口输出，同时不影响代码修改和烧录：

```bash
# 启动监听（后台跑，数据实时可见）
python proj/tools/serial_listener.py <COM口> [波特率]

# 示例：在监听的同时，仍可编译烧录
python proj/tools/serial_listener.py COM8 9600
arduino-cli compile --fqbn arduino:avr:uno --upload --port COM8 <sketch目录>
```

### 烧录测试确认

两块板子均用测试程序（LED闪烁 + 串口输出）验证通过：

```bash
# 先编译
arduino-cli compile --fqbn arduino:avr:uno --output-dir proj/test_board/build proj/test_board

# 大板（PlayKit）→ COM5
"E:/arduino-1.8.19/hardware/tools/avr/bin/avrdude" -C"E:/arduino-1.8.19/hardware/tools/avr/etc/avrdude.conf" -v -patmega328p -carduino -PCOM5 -b115200 -D -Uflash:w:proj/test_board/build/test_board.ino.hex:i

# 小板（Arduino UNO）→ COM6
"E:/arduino-1.8.19/hardware/tools/avr/bin/avrdude" -C"E:/arduino-1.8.19/hardware/tools/avr/etc/avrdude.conf" -v -patmega328p -carduino -PCOM6 -b115200 -D -Uflash:w:proj/test_board/build/test_board.ino.hex:i
```

测试代码 `proj/test_board/test_board.ino`：板载LED每秒闪烁，串口9600波特率每秒输出 `Hello from PlayKit!`。

### LoRa 通信验证

使用原版实验2（半双工双向串口通信）代码验证通过：

| 测试 | 频率 | 结果 |
|------|------|------|
| 原版（默认D10=SS） | 433MHz | 两块板子均初始化成功，LoRa 互相收发正常，RSSI 约 -70dBm |
| 修改为 7 组频段 | 413MHz | 初始化成功，收发正常，RSSI 约 -70dBm |

关键要点：
- LoRa 模块使用 **默认 SPI 引脚（D10=SS）**，不需要调用 `LoRa.setPins(A3)`。实验资料中片选说明文档虽然提到接 A3，但 PlayKit 配套的 LoRa 模块实际接的是 D10(SS)
- 7 组（410-416MHz）写入 `LoRa.begin(413E6)` 即可正常工作

用到的测试代码：
- `proj/test_freq/test_freq.ino` — 413MHz 发送端（每3秒发 ping）
- `proj/test_freq_recv/test_freq_recv.ino` — 413MHz 接收端（打印收到内容和 RSSI）

### 调试流程

```
1. 我写代码 → 你插好板子告诉我 COM 口
2. 我编译烧录 → arduino-cli compile + avrdude 6.3 上传
3. 我启动监听 → python proj/tools/serial_listener.py COMx 9600
4. 你操作板子（按键、LoRa收发等）
5. 代码中 Serial.println() 输出 → 我实时收到 → 直接反馈问题
6. 我改代码 → 回到第2步循环
```

### 注意

- `arduino-cli` 自带的 avrdude 8.0 之前配置文件有 bug，无法直接 `--upload`。已修复：将 IDE 自带的 avrdude 6.3 的 exe、DLL 和配置文件复制到 8.0 目录，现已可正常使用 `--upload`。
- 两个板子都是 ATmega328P，编译用 `--fqbn arduino:avr:uno`
3. 我启动 listen.py 后台监听串口
4. 你操作板子（按键、LoRa收发等）
5. 代码中 Serial.println() 的输出 → 我实时收到 → 直接反馈问题
6. 我改代码 → 回到第2步循环
```

## 参考项目

项目根目录下的 [reference.md](reference.md) 记录了一个低速星型无线通信系统的分析，其通信协议（帧结构、ACK+超时重传、MCS校验）和软件架构（Timer类、位图管理、模块化分层）可参考复用。该代码位于 `reference/` 目录中。

## 参考资料

- 陈吕州. Arduino程序设计基础（第2版）. 北京航空航天大学出版社, 2015
- 沈金鑫. Arduino与LabVIEW开发实战. 机械工业出版社, 2014
- 李培毅. Arduino实验案例指导手册
- NI-VISA 驱动: https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html（LabVIEW 2019 选对应版本即可）
- Ra-02 规格书: 安信可科技（SX1278，410-525MHz，SPI接口）
- LoRa 库: https://github.com/sandeepmistry/arduino-LoRa（对应 arduino-LoRa-master.rar）
