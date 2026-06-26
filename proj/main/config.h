#ifndef CONFIG_H
#define CONFIG_H

// 7组: 410-416 MHz, 8bit SF
#define LORA_FREQ 413E6
#define LORA_SF 8
#define LORA_SYNC_WORD 0xcd

// 地址定义
#define ADDR_NONE 0x30       // ASCII '0'
#define ADDR_FIRST 0x31      // ASCII '1'
#define ADDR_LAST 0x34       // ASCII '4', 最多4个节点
#define ADDR_BCAST 0x41      // ASCII 'A', 广播地址
#define MAX_NODES 4

// 功能码
#define F_JOIN_REQ 'J'       // 申请入网
#define F_JOIN_ACK 'j'       // 同意入网 + 分配地址
#define F_HEARTBEAT 'H'      // 心跳
#define F_LEAVE 'L'          // 退网
#define F_LEAVE_ACK 'l'      // 退网确认
#define F_DATA 'D'           // 单播数据
#define F_DATA_ACK 'd'       // 数据确认
#define F_BCAST 'B'          // 广播数据
#define F_CLAIM 'C'          // 竞选声明：多个候选节点同时存在时，比随机数大小决定谁入网

// 时序 (ms)
#define SCAN_LISTEN_TIME 3000 // 监听时长：只收不发，听不到网络活动才进入竞选
#define SCAN_JITTER_MAX 2000  // 监听额外随机等待（0~2s），各板完成时间不同
#define CLAIM_WINDOW 1000     // 竞选窗口：发声明 + 收别人的声明，比随机数大小
#define HEARTBEAT_INTERVAL 1500
#define NEIGHBOR_TIMEOUT 6000
#define ACK_TIMEOUT 500      // 等待 ACK 超时（单播）
#define RETRY_MAX 3          // 入网重试次数
#define LEAVE_TIMEOUT 500
#define RAPID_BEACONS 5     // 快速宣告次数
#define RAPID_BEACON_INTERVAL 100

// 串口命令
#define CMD_STATUS 'S'
#define CMD_SEND 'D'
#define CMD_LEAVE 'L'
#define CMD_BCAST 'B'
#define CMD_TEST 'T'          // 网络测试：T<n> 连续发 n 个测试包并统计
#define CMD_RESET_STATS 'R'   // 重置统计

#define TEST_SEND_INTERVAL 500 // 测试模式下发包间隔(ms)
#define RSSI_SAMPLE_MAX 20     // RSSI 采样队列长度

#endif
