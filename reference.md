# 参考项目分析 — 低速星型无线通信系统

参考项目位于 `reference/`，是一个"低速星型无线通信系统设计"（1个中心节点 + 3个终端节点），虽然拓扑结构与我们的无中心自组网络不同，但通信协议和软件架构有很高的参考价值。

## 项目结构

```
reference/arduino_code/
├── central node/         # 中心节点
│   └── CN/
│       ├── CN.ino       # 主循环（7阶段）
│       ├── config.h     # 配置宏
│       ├── CenNode.h/cpp # 中心节点类
│       ├── Timer.h/cpp  # 非阻塞定时器
│       ├── includes.h/subincludes.h  # 头文件组织
│       └── ...
└── termnial/terminal/    # 终端节点
    ├── terminal.ino     # 主循环
    ├── config.h         # 配置宏
    ├── Terminal.h/cpp   # 终端节点类
    ├── Timer.h/cpp      # 非阻塞定时器
    └── ...
```

## 通信协议（帧结构）

每帧固定格式（长度可变）：

```
| DAddr(1) | SAddr(1) | Function(1) | DataLen(1) | MCS(1) | MsgData(N) |
```

| 字段 | 长度 | 说明 |
|------|------|------|
| DAddr | 1 byte | 目的地址（ASCII字符 '0'~'4'） |
| SAddr | 1 byte | 源地址（ASCII字符 '0'~'3'） |
| Function | 1 byte | 功能位（见下） |
| DataLen | 1 byte | 数据长度（字符形式） |
| MCS | 1 byte | 校验和：DAddr^SAddr^Function^DataLen |
| MsgData | N byte | 实际数据内容 |

### 功能位定义

| 功能 | 值 | 方向 | 用途 |
|------|-----|------|------|
| 退网 | '0' | 双向 | 要求/确认退网 |
| 建立连接 | '1' | 中心→终端 | 通信链路建立 |
| 数据请求/回复 | '2' | 双向 | 请求发送数据或回复 |
| 询问存在 | '3' | 中心→终端 | 心跳检测是否在线 |
| 保持联系 | '4' | 中心→终端 | 维持连接 |
| 广播（邀请入网） | '5' | 中心→广播 | 发现新节点 |
| 申请入网 | '6' | 终端→中心 | 节点请求接入 |
| 允许入网 | '7' | 中心→终端 | 同意节点接入 |
| 更改频率 | '8' | 中心→终端 | 动态调整信道参数 |

## 可靠通信机制

### ACK + 超时重传
- 发送消息后等待 ACK 回复
- 设置超时计时器（如 MAX_WAIT_TIME = 800ms）
- 超时未收到 ACK → 重试或标记节点掉线

### 校验方式
- **无线帧校验（MCS）**：XOR 校验，`DAddr ^ SAddr ^ Function ^ DataLen`
- **串口帧校验（FCS）**：奇偶校验序列，用于 PC ↔ 板子有线通信

### 串口帧封装（PC ↔ 中心节点）
```
| '#' (同步位) | FCS(2) | Function(1) | Data(N) | '*' (结束位) |
```

## 软件架构亮点

### 1. Timer 非阻塞定时器
基于 `millis()` 实现，不阻塞主循环。可直接复用：

```cpp
class Timer {
  unsigned long t_start;
  unsigned long t_ineterval;
public:
  void new_start(unsigned long t_ineterval_in);  // 重置计时
  bool result();                                   // 是否到时间
  void zero();                                     // 关闭
};
```

### 2. 位图管理节点状态
使用一个 byte 的每个 bit 表示一个终端是否在线：

```cpp
byte TerAcs = 0x00;        // 接入映射表
// AddrMaskMap: {0x00, 0x01, 0x02, 0x04}
// TerAcs & 0x01 → 节点1在网
// TerAcs |= 0x02 → 标记节点2入网
// TerAcs &= ~0x01 → 标记节点1退网
```

### 3. 头文件分层管理
- `config.h` — 所有宏定义集中管理（地址、同步字、超时时间等）
- `subincludes.h` — 库引用 + 结构体定义（Message 帧结构）
- `includes.h` — 汇总包含所有自定义模块头文件
- 主 `.ino` 文件只 `#include "includes.h"`，保持干净

### 4. Message 结构体定义

```cpp
typedef struct MESSAGE {
  byte DAddr;      // 目的地址
  byte SAddr;      // 源地址
  byte Function;   // 功能位
  byte DataLen;    // 数据长度（字符形式）
  byte MCS;        // 校验和
  String MsgData;  // 数据
} Message;
```

### 5. 主循环分阶段执行（中心节点）

```
1. 接收主机命令（PC→板子串口）
2. 轮询终端获取数据
3. 向主机反馈数据（板子→PC串口）
4. 与终端保持联系（发送心跳）
5. 检测可能掉线的终端
6. 广播（邀请新节点入网）
7. 通知接入情况
```

## 对无中心自组网络的参考价值

### 可直接复用的
- **帧结构格式** — DAddr/SAddr/Function/DataLen/MCS 结构
- **Timer 类** — 非阻塞定时器，完全通用
- **MCS XOR 校验** — 简单高效
- **ACK + 超时重传** — 可靠通信的基础
- **头文件分层管理** — config.h / subincludes.h / includes.h 模式
- **位图管理节点** — 适合对等网络的邻居表管理

### 需要改造的
- **拓扑结构** — 星型 → 无中心对等网络：每个节点既是"中心"也是"终端"
- **入网流程** — 中心分配 → 分布式协商：任意节点发起广播，周边节点响应
- **通信方式** — 中心中转 → P2P 直连：任意两节点可直接通信
- **状态机** — 单一角色状态 → 多角色复合状态（空闲/监听/组网/通信/退网）
