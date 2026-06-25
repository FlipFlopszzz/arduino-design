# 项目结构说明

## 目录结构

```
E:/arduino_design/
├── CLAUDE.md           # 项目全局说明（课程信息、硬件、开发环境）
├── preparation.md      # 前置工作清单
├── TODO.md             # 待完成任务
├── reference.md        # 参考项目（星型网络）分析与借鉴
├── structure.md        # ← 本文件：项目架构详解
│
└── proj/
    ├── main/           # 主项目代码（唯一追踪的代码目录）
    │   ├── main.ino    # 入口文件
    │   ├── config.h    # 配置参数
    │   └── Node.h      # 核心逻辑（Node类）
    │
    ├── test/           # 测试代码，供参考
    │   ├── test_board/         # 板子基础测试（LED闪烁）
    │   ├── test_original/      # LoRa原始实验1（一收一发）
    │   ├── test_duplex/        # LoRa原始实验2（半双工）
    │   ├── test_freq/          # 413MHz 频率测试
    │   ├── test_freq_recv/     # 413MHz 接收测试
    │   ├── test_labview1/      # LabVIEW LED控制实验
    │   ├── test_labview2/      # LabVIEW 模拟值采集
    │   ├── led_test/           # LED 串口控制
    │   └── lora_diag/         # LoRa 初始化诊断
    │
    └── tools/
        ├── serial_listener.py  # 串口监听脚本（防DTR复位）
        └── test_3node.py       # 三节点自动化测试脚本
```

---

## 文件功能

### main.ino
项目入口，只做两件事：
```cpp
PeerNode node;     // 创建节点对象
node.setup();      // 初始化（串口、LoRa、开始扫描）
node.loop();       // 不断循环处理网络事件
```

### config.h
所有配置参数集中管理，分四类：

**硬件参数** — LoRa 频段、扩频因子、同步字：

| 宏 | 值 | 说明 |
|------|-----|------|
| LORA_FREQ | 413E6 | 7 组频段（410-416MHz 中间值） |
| LORA_SF | 8 | 8bit 扩频因子 |
| LORA_SYNC_WORD | 0xcd | 同步字 |

**地址定义**：

| 宏 | 值(ASCII) | 说明 |
|------|----------|------|
| ADDR_NONE | '0' | 未分配地址，新节点 |
| ADDR_FIRST | '1' | 第一个可分配地址 |
| ADDR_LAST | '4' | 最后一个可分配地址 |
| ADDR_BCAST | 'A' | 广播地址 |

**功能码** — 每种 LoRa 数据包的类型标识：

| 宏 | ASCII | 说明 | 方向 |
|----|-------|------|------|
| F_JOIN_REQ | 'J' | 申请入网 | 新节点 → 网内节点 |
| F_JOIN_ACK | 'j' | 同意入网 + 分配地址 | 网内节点 → 新节点 |
| F_HEARTBEAT | 'H' | 心跳，携带路由表 | 全网广播 |
| F_LEAVE | 'L' | 通知退网 | 退网节点 → 广播 |
| F_LEAVE_ACK | 'l' | 退网确认 | 收 → 退网节点 |
| F_DATA | 'D' | 单播数据 | 任意节点 |
| F_DATA_ACK | 'd' | 数据确认 | 接收方 → 发送方 |
| F_BCAST | 'B' | 广播数据 | 任意 → 全网 |
| F_CLAIM | 'C' | 竞选声明 | 新节点（未入网时） |

**时序参数** — 所有时间间隔单位 ms：

| 宏 | 当前值 | 说明 |
|------|-------|------|
| SCAN_LISTEN_TIME | 6000 | 新人监听时长 |
| SCAN_JITTER_MAX | 4000 | 监听随机抖动 |
| CLAIM_WINDOW | 1500 | 竞选窗口 |
| HEARTBEAT_INTERVAL | 3000 | 心跳间隔 |
| NEIGHBOR_TIMEOUT | 12000 | 超时判离线 |
| ACK_TIMEOUT | 800 | ACK 等待超时 |
| RETRY_MAX | 3 | 入网重试次数 |
| RAPID_BEACONS | 10 | 刚入网时快速宣告次数 |
| RAPID_BEACON_INTERVAL | 100 | 快速宣告间隔 |

### Node.h
整个项目的核心，定义 `PeerNode` 类。所有网络逻辑在这个文件中。

---

## Node.h 结构

### 数据定义

**RouteEntry** — 路由表项
```cpp
typedef struct {
  bool online;
  unsigned long lastSeen;  // 上次收到心跳的 millis()
} RouteEntry;
```

**Message** — LoRa 帧结构
```cpp
typedef struct {
  byte DAddr;      // 目的地址
  byte SAddr;      // 源地址
  byte Function;   // 功能码
  byte DataLen;    // 数据长度（字符形式）
  byte MCS;        // XOR 校验和
  String MsgData;  // 数据内容
} Message;
```

**NodeState** — 节点状态机
```cpp
enum NodeState {
  STATE_SCANNING,    // 扫描监听
  STATE_CLAIMING,    // 竞选
  STATE_JOINING,     // 加入
  STATE_IN_NETWORK,  // 已入网
  STATE_LEAVING      // 退网
};
```

### PeerNode 核心字段

| 字段 | 类型 | 说明 |
|------|------|------|
| state | NodeState | 当前状态 |
| myAddr | byte | 本机地址（'0'=未分配，'1'~'4'=已入网） |
| route[] | RouteEntry[4] | 路由表，下标对应地址'1'~'4' |
| joinTarget | byte | 加入时目标节点地址 |
| joinToken | byte | 当前 JOIN_REQ 的随机令牌 |
| canClaim | bool | 是否允许参加竞选（loser 后关闭） |
| testMode | bool | 是否在测试模式 |

### PeerNode 主要方法

| 方法 | 说明 |
|------|------|
| setup() | 初始化串口、LoRa、随机种子，启动扫描 |
| loop() | 主循环：收包 → 按状态分发处理 |
| startScan() | 进入扫描监听状态 |
| startClaiming() | 进入竞选状态 |
| sendJoinReq() | 发 JOIN_REQ（带随机令牌） |
| sendMsg() | 发送 LoRa 包（自动计算 MCS） |
| recvMsg() | 接收 LoRa 包（MCS 校验 + RSSI/SNR 采样） |
| doHeartbeat() | 定时广播心跳 |
| processSerial() | 处理 PC 串口命令 |
| sendUnicast() | 单播发送 |
| sendBroadcast() | 广播发送 |
| printStatus() | 打印路由表和统计 |

---

## LoRa 帧结构

所有无线数据包统一格式：

```
| DAddr(1) | SAddr(1) | Function(1) | DataLen(1) | MCS(1) | MsgData(N) |
```

每个字段用 `LoRa.print()` 逐字节发送 ASCII 字符。

**MCS 校验**：`DAddr ^ SAddr ^ Function ^ DataLen`，接收端重算对比，不一致则丢弃。

**DataLen**：使用字符形式，即实际长度 + '0'。例如数据长度 4 → 存为 ASCII 字符 '4'。

---

## 串口命令（PC ↔ 板子，9600 波特率）

| 命令 | 格式 | 说明 |
|------|------|------|
| S | 单字符 | 打印本机地址、路由表、统计数据 |
| D | D<addr><data> | 单播，如 `D2Hello` |
| B | B<data> | 广播，如 `BHello` |
| T | T<addr>[n] | ping 测试，如 `T2`（10次）或 `T220`（20次） |
| L | 单字符 | 本机退网，之后自动重新入网 |
| R | 单字符 | 重置统计数据 |

---

## 完整入网流程

```
                        ┌─────────────────────┐
                        │    上电 setup()       │
                        │  Serial, LoRa, 随机种子│
                        └────────┬────────────┘
                                 │
                                 ▼
                        ┌─────────────────────┐
            ┌───────────│  SCANNING (6~10s)    │
            │           │  只收不发，纯监听     │
            │           └────────┬────────────┘
            │                    │
            │          ┌─────────┴──────────┐
            │          │                    │
            │          ▼                    ▼
            │   听到心跳              6~10s 到
            │  (有网络存在)         (没有任何网络)
            │          │                    │
            │          ▼                    ▼
            │   ┌─────────────┐   ┌──────────────────┐
            │   │  JOINING    │   │  CLAIMING (1.5s) │
            │   │ 发 JOIN_REQ │   │  广播竞选 + 比大小 │
            │   │ 等 JOIN_ACK │   └────────┬─────────┘
            │   └────────┬────┘            │
            │            │          ┌──────┴────────┐
            │            │          │               │
            │            │          ▼               ▼
            │            │   我的随机数最大   有人比我大
            │            │   (成为 WINNER)   (我是 LOSER)
            │            │          │               │
            │            │          ▼               ▼
            │            │  自分配 '1'         canClaim=false
            │            │  快速心跳 x10      回 SCANNING
            │            │                          │
            │            │                          ▼
            │            │                   听到 WINNER 心跳
            │            │                   发 JOIN_REQ
            │            │                          │
            │            ▼                          ▼
            │     ┌──────────────────────┐
            └─────│  IN_NETWORK          │
                  │  · 每 3s 心跳广播     │
                  │  · 处理数据/广播      │
                  │  · 12s 超时判离线     │
                  │  · 处理串口命令       │
                  └──────────────────────┘
```

---

## 入网关键要点

### 1. 扫描（SCANNING）
- 持续 6~10 秒（6s + ADC 噪声 0~4s 随机抖动）
- **只收不发**，防止干扰
- 听到 `F_HEARTBEAT` + 地址 '1'~'4' → 转 JOINING
- 超时 → 允许竞选则转 CLAIMING，否则继续监听

### 2. 竞选（CLAIMING）
- 解决"多个新节点同时上电，谁当第一个"的问题
- 用 20 次 ADC 噪声累加生成大随机数，芯片不同读数几乎一定不同
- 广播 `F_CLAIM` 声明
- 1.5 秒内比较谁最大：
  - WINNER → 自分配 '1'，快速心跳 10 次宣告存在
  - LOSER → `canClaim=false`，重新扫描只加入不竞选

### 3. 加入（JOINING）
- 生成随机令牌（1~255）
- 发 `F_JOIN_REQ`（令牌 + "?"）
- 等 800ms，收到 `F_JOIN_ACK`（回传令牌 + 分配地址）
  - **令牌匹配** → 设为分配地址 → 入网
  - **令牌不匹配** → 丢弃（防止两个新节点抢同一个 ACK）
- 800ms 超时 → 重试，3 次失败 → 回扫描

### 4. 入网后（IN_NETWORK）
- 每 3 秒广播心跳，携带路由表
- 收到心跳 → 直接更新 sender 的 lastSeen
- 心跳中携带的路由表 → 间接学习其他节点（刷新 lastSeen，防止信号差被误判离线）
- 12 秒没任何节点收到某节点的心跳 → 判离线

### 5. 心跳（HEARTBEAT）
已入网节点定期宣告存在，格式：

```
| DAddr='A' | SAddr='2' | Function='H' | DataLen='4' | MCS=? | MsgData="1110" |
```

MsgData 的 4 位是路由表，第 i 位 = 地址 i+1 的在线状态：
- `"1110"` = 节点 1/2/3 在线，节点 4 离线

收到心跳的节点不仅知道 sender 在线，还通过路由表间接知道其他节点状态（**间接路由学习**）。

---

## 网络维持

### 心跳机制
- 已入网节点每 3 秒广播一次心跳
- 心跳携带**本机视角的路由表**（4 位：1/2/3/4 是否在线）
- 刚入网时 10 次快速宣告（100ms 间隔），让大家立刻知道新节点

### 超时判离线
- 每个节点记录路由表中其他节点的 lastSeen
- 任意节点 12 秒内没有被**任何人**直接或间接听到 → 判离线
- 间接学习也会刷新 lastSeen，所以只要网络中有一个人能联系到该节点，就不会误判

### 路由表更新
| 事件 | 动作 |
|------|------|
| 收到心跳 | 标记发送者在线，刷新 lastSeen |
| 心跳中间接学习 | 标记被提到节点在线，刷新 lastSeen |
| 收到 JOIN_REQ | 分配地址，标记新节点在线 |
| 收到 LEAVE | 标记节点离线 |
| 12 秒超时 | 标记节点离线 |

---

## 统计功能

### 数据采集
- `sendMsg()` / `recvMsg()` 自动计数发送/接收/ACK/心跳
- `recvMsg()` 通过 `LoRa.packetRssi()` 和 `LoRa.packetSnr()` 采样信号强度
- RSSI 采样队列 20 个，环形缓冲，支持 min/avg/max

### 网络质量测试（T 命令）
```
T2        → ping 节点 2 十次
T310      → ping 节点 3 十次
T120      → ping 节点 1 二十次
```

测试模式连续发 `F_DATA`，每 500ms 一个，统计收到的 `F_DATA_ACK`：
```
Sent: 10
ACK: 7
Loss: 30%
Time: 4563ms
RTT: ~651ms
```

### S 命令输出示例
```
========================
*** NODE 1 ***
========================
--- ROUTE ---
  1: SELF
  2: ON
  4: ON
=== STATS ===
TX packets: 5
RX packets: 3
ACK sent: 2
ACK recv: 3
CRC good: 10
CRC bad: 0
RSSI: -60/-45/-27 dBm (min/avg/max)
SNR: 11.1 dB (avg)
```
