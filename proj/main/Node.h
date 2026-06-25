#ifndef NODE_H
#define NODE_H

#include <Arduino.h>
#include <LoRa.h>
#include <SPI.h>
#include "config.h"

// ====================== 路由表项 ======================
typedef struct {
  bool online;
  unsigned long lastSeen;
} RouteEntry;

// ====================== 帧结构 ======================
typedef struct {
  byte DAddr;
  byte SAddr;
  byte Function;
  byte DataLen;
  byte MCS;
  String MsgData;
} Message;

// ====================== 节点状态 ======================
enum NodeState {
  STATE_SCANNING,
  STATE_CLAIMING,
  STATE_JOINING,
  STATE_IN_NETWORK,
  STATE_LEAVING
};

// ====================== 主类 ======================
class PeerNode {
private:
  NodeState state;
  byte myAddr;
  bool isInitiator;

  // 路由表：下标 0~3 对应地址 '1'~'4'
  RouteEntry route[MAX_NODES];

  unsigned long scanEndTime;
  unsigned long lastHeartbeat;
  int rapidBeaconCount;
  unsigned long joinTimer;
  int joinRetries;
  byte joinTarget;
  byte joinToken;      // 当前 JOIN_REQ 的随机令牌

  unsigned long leaveTimer;

  // ---------------------- 网络统计 ----------------------
  unsigned long packetsSent;
  unsigned long packetsReceived;
  unsigned long heartbeatsSent;
  unsigned long heartbeatsReceived;
  unsigned long acksSent;
  unsigned long acksReceived;
  unsigned long rxGood;        // 通过校验的接收数
  unsigned long rxBad;         // 校验失败的接收数
  int rssiSamples[RSSI_SAMPLE_MAX];
  int rssiSampleCount;
  int rssiSampleIdx;
  int rssiMin;                 // 本周期最小值
  int rssiMax;                 // 本周期最大值
  long rssiSum;                // 本周期总和（用于平均）
  int snrSamples[RSSI_SAMPLE_MAX];
  int snrSampleCount;
  int snrSampleIdx;

  // 竞选阶段
  bool claiming;
  unsigned long claimEndTime;
  unsigned long myClaim;        // 我的竞选值
  unsigned long bestClaim;      // 听到的最大竞选值
  bool claimBroadcastSent;

  // 测试模式
  bool testMode;
  unsigned long testStartTime;
  int testPacketsToSend;
  int testPacketsSent;
  int testAcksReceived;
  unsigned long testLastSend;
  byte testTargetAddr;

  // ---------------------- 工具 ----------------------
  int addrIdx(byte addr) { return addr - ADDR_FIRST; }
  byte idxAddr(int i)    { return (byte)(ADDR_FIRST + i); }

  byte genMCS(Message& m) {
    return m.DAddr ^ m.SAddr ^ m.Function ^ m.DataLen;
  }

  int countOnline() {
    int n = 1;  // 本机始终在线
    for (int i = 0; i < MAX_NODES; i++)
      if (i != addrIdx(myAddr) && route[i].online) n++;
    return n;
  }

  byte pickUnusedAddr() {
    for (int i = 0; i < MAX_NODES; i++) {
      if (i == addrIdx(myAddr)) continue;
      if (!route[i].online) return idxAddr(i);
    }
    return ADDR_NONE;
  }

  void markOnline(byte addr) {
    int i = addrIdx(addr);
    if (i < 0 || i >= MAX_NODES || i == addrIdx(myAddr)) return;
    if (!route[i].online) {
      Serial.print(F("[NET] "));
      Serial.print((char)addr);
      Serial.println(F(" ON"));
    }
    route[i].online = true;
    route[i].lastSeen = millis();
  }

  void markOffline(byte addr) {
    int i = addrIdx(addr);
    if (i < 0 || i >= MAX_NODES) return;
    if (route[i].online) {
      Serial.print(F("[NET] "));
      Serial.print((char)addr);
      Serial.println(F(" OFF"));
    }
    route[i].online = false;
    route[i].lastSeen = 0;
  }

  void resetRoute() {
    for (int i = 0; i < MAX_NODES; i++) {
      route[i].online = false;
      route[i].lastSeen = 0;
    }
  }

  // ---------------------- 收发 ----------------------
  void sendMsg(Message& m) {
    m.MCS = genMCS(m);
    if (m.Function == F_HEARTBEAT) heartbeatsSent++;
    else if (m.Function == F_DATA || m.Function == F_BCAST) packetsSent++;
    else if (m.Function == F_DATA_ACK || m.Function == F_LEAVE_ACK || m.Function == F_JOIN_ACK) acksSent++;
    LoRa.beginPacket();
    LoRa.print((char)m.DAddr);
    LoRa.print((char)m.SAddr);
    LoRa.print((char)m.Function);
    LoRa.print((char)m.DataLen);
    LoRa.print((char)m.MCS);
    LoRa.print(m.MsgData);
    LoRa.endPacket();
  }

  bool recvMsg(Message& m) {
    if (LoRa.parsePacket() == 0) return false;
    String raw;
    while (LoRa.available()) raw += (char)LoRa.read();
    if (raw.length() < 5) return false;

    m.DAddr = (byte)raw.charAt(0);
    if (m.DAddr != myAddr && m.DAddr != ADDR_BCAST && m.DAddr != ADDR_NONE) return false;
    m.SAddr = (byte)raw.charAt(1);
    m.Function = (byte)raw.charAt(2);
    m.DataLen = (byte)raw.charAt(3);
    m.MCS = (byte)raw.charAt(4);
    raw.remove(0, 5);
    m.MsgData = raw;
    bool valid = (m.MCS == genMCS(m));
    if (valid) {
      rxGood++;
      // 采样 RSSI
      int rssi = LoRa.packetRssi();
      float snr = LoRa.packetSnr();
      if (rssiSampleCount < RSSI_SAMPLE_MAX) {
        rssiSamples[rssiSampleIdx] = rssi;
        rssiSum += rssi;
        if (rssiSampleCount == 0) { rssiMin = rssi; rssiMax = rssi; }
        else { if (rssi < rssiMin) rssiMin = rssi; if (rssi > rssiMax) rssiMax = rssi; }
        rssiSampleIdx = (rssiSampleIdx + 1) % RSSI_SAMPLE_MAX;
        if (rssiSampleCount < RSSI_SAMPLE_MAX) rssiSampleCount++;
      }
      if (snrSampleCount < RSSI_SAMPLE_MAX) {
        snrSamples[snrSampleIdx] = (int)(snr * 10);
        snrSampleIdx = (snrSampleIdx + 1) % RSSI_SAMPLE_MAX;
        if (snrSampleCount < RSSI_SAMPLE_MAX) snrSampleCount++;
      }
    } else {
      rxBad++;
    }
    return valid;
  }

  // ---------------------- 心跳数据编码/解码 ----------------------
  //
  // 心跳 MsgData 格式: "1011"
  //  每个字符代表地址1~4的在线状态
  //  '1'=在线 '0'=离线，第0位=地址1，第1位=地址2，...

  String encodeRoute() {
    String s;
    for (int i = 0; i < MAX_NODES; i++)
      s += route[i].online ? '1' : '0';
    return s;
  }

  void decodeRoute(byte sender, String& data) {
    for (int i = 0; i < MAX_NODES && i < (int)data.length(); i++) {
      if (data.charAt(i) == '1') {
        byte reportedAddr = idxAddr(i);
        if (reportedAddr != myAddr && reportedAddr != sender) {
          // 间接学习：其他节点说 reportedAddr 在线，刷新 lastSeen 防止超时误判
          // 即使节点自身的直连心跳不稳定，只要网络中有人能联系到它，就不该判离线
          if (!route[i].online) {
            Serial.print(F("[NET] Learn "));
            Serial.print((char)reportedAddr);
            Serial.println(F(" via hb"));
          }
          route[i].online = true;
          route[i].lastSeen = millis();
        }
      }
    }
  }

  // ---------------------- 状态 ----------------------
  void setState(NodeState s) { state = s; }

public:
  void resetStats() {
    packetsSent = 0; packetsReceived = 0;
    heartbeatsSent = 0; heartbeatsReceived = 0;
    acksSent = 0; acksReceived = 0;
    rxGood = 0; rxBad = 0;
    rssiSampleCount = 0; rssiSampleIdx = 0;
    rssiMin = 0; rssiMax = 0; rssiSum = 0;
    snrSampleCount = 0; snrSampleIdx = 0;
    testMode = false; testPacketsToSend = 0;
    testPacketsSent = 0; testAcksReceived = 0;
  }

  PeerNode() : state(STATE_SCANNING), myAddr(ADDR_NONE), isInitiator(false),
               lastHeartbeat(0), rapidBeaconCount(0), joinRetries(0),
               joinTarget(ADDR_NONE), joinTimer(0), leaveTimer(0), joinToken(0) {
    resetRoute();
    resetStats();
  }

  void setup() {
    Serial.begin(9600);
    while (!Serial);

    // ADC 噪声随机种子
    unsigned long s = 0;
    for (int i = 0; i < 10; i++) s = s * 7 + analogRead(A0);
    randomSeed(s);

    if (!LoRa.begin(LORA_FREQ)) {
      Serial.println(F("LoRa fail"));
      while (1);
    }
    LoRa.setSpreadingFactor(LORA_SF);
    LoRa.setSyncWord(LORA_SYNC_WORD);
    LoRa.enableCrc();
    Serial.println(F("[SYS] OK"));
    startScan();
  }

  void loop() {
    Message msg;
    bool got = recvMsg(msg);

    switch (state) {
      case STATE_SCANNING:
        if (got) onScanMsg(msg);
        else checkScanTimeout();
        break;
      case STATE_CLAIMING:
        if (got) onClaimMsg(msg);
        checkClaimTimeout();
        break;
      case STATE_JOINING:
        if (got) onJoinMsg(msg);
        checkJoinTimeout();
        break;
      case STATE_IN_NETWORK:
        if (got) onNetMsg(msg);
        doHeartbeat();
        if (testMode) handleTestMode();
        checkTimeouts();
        processSerial();
        break;
      case STATE_LEAVING:
        checkLeaveTimeout();
        break;
    }
  }

  // ==================== 扫描（纯监听，不发任何数据） ====================
  void startScan() {
    setState(STATE_SCANNING);
    unsigned long jitter = (analogRead(A0) + analogRead(A1) + analogRead(A2)) % (SCAN_JITTER_MAX + 1);
    scanEndTime = millis() + SCAN_LISTEN_TIME + jitter;
    Serial.println(F("[S] Listen"));
  }

  void onScanMsg(Message& msg) {
    // 只对心跳消息反应，避免被其他组的干扰数据误导
    if (msg.Function == F_HEARTBEAT && msg.SAddr >= ADDR_FIRST && msg.SAddr <= ADDR_LAST) {
      joinTarget = msg.SAddr;
      joinRetries = 0;
      joinTimer = 0;
      setState(STATE_JOINING);
      sendJoinReq();
      joinTimer = millis();
      Serial.print(F("[S] Join via "));
      Serial.println((char)joinTarget);
    }
  }

  void checkScanTimeout() {
    if (millis() < scanEndTime) return;
    // 扫描结束，没听到网络 → 进入竞选
    startClaiming();
  }

  // ==================== 竞选（多个新节点同时存在时比随机数大小） ====================
  void startClaiming() {
    setState(STATE_CLAIMING);
    claiming = false;
    claimBroadcastSent = false;
    bestClaim = 0;
    claimEndTime = millis() + CLAIM_WINDOW;

    // 用 ADC 硬件噪声生成竞选值（各芯片不同，几乎唯一）
    myClaim = 0;
    for (int i = 0; i < 20; i++) {
      myClaim = myClaim * 7 + analogRead(A0);
      delayMicroseconds(500);
    }
    myClaim ^= micros();  // 加入上电时间差

    Serial.print(F("[C] Claiming "));
    Serial.println(myClaim);
  }

  void onClaimMsg(Message& msg) {
    // 竞选期间听到已有节点的心跳 → 放弃竞选，加入
    if (msg.Function == F_HEARTBEAT && msg.SAddr >= ADDR_FIRST && msg.SAddr <= ADDR_LAST) {
      joinTarget = msg.SAddr;
      joinRetries = 0;
      joinTimer = 0;
      setState(STATE_JOINING);
      sendJoinReq();
      joinTimer = millis();
      Serial.print(F("[S] Join via "));
      Serial.println((char)joinTarget);
      return;
    }
    // 听到其他竞选声明 → 比较大小
    if (msg.Function == F_CLAIM && msg.SAddr == ADDR_NONE) {
      unsigned long theirClaim = msg.MsgData.toInt();
      if (theirClaim > bestClaim) {
        bestClaim = theirClaim;
        Serial.print(F("[C] Beat by "));
        Serial.println(bestClaim);
      }
    }
  }

  void checkClaimTimeout() {
    // 发送竞选声明（只发一次）
    if (!claimBroadcastSent) {
      claimBroadcastSent = true;
      Message c;
      c.DAddr = ADDR_BCAST;
      c.SAddr = ADDR_NONE;
      c.Function = F_CLAIM;
      c.MsgData = String(myClaim);
      c.DataLen = (byte)(c.MsgData.length() + '0');
      sendMsg(c);
    }

    if (millis() < claimEndTime) return;

    // 竞选窗口结束，比大小
    if (bestClaim > myClaim) {
      // 有人比我大 → 等待 winner 建立网络后加入
      Serial.print(F("[C] Lost to "));
      Serial.print(bestClaim);
      Serial.println(F(", waiting"));
      // 听一轮完整的扫描窗口确保能收到 winner 的心跳
      startScan();
      return;
    }

    // 我是 winner → 自分配为节点 1
    myAddr = ADDR_FIRST;
    isInitiator = true;
    route[addrIdx(myAddr)].online = true;
    route[addrIdx(myAddr)].lastSeen = millis();
    rapidBeaconCount = RAPID_BEACONS;
    lastHeartbeat = 0;
    setState(STATE_IN_NETWORK);
    Serial.print(F("[NET] Self "));
    Serial.println((char)myAddr);
    printNodeBanner();
  }

  // ==================== 加入（带令牌匹配，防止两个新节点收到同一个 ACK 时都认领） ====================
  void sendJoinReq() {
    joinToken = (byte)random(1, 256);  // 随机令牌
    Message req;
    req.DAddr = joinTarget;
    req.SAddr = ADDR_NONE;
    req.Function = F_JOIN_REQ;
    req.DataLen = '2';                 // 数据长度 = 2 (令牌 + '?')
    req.MsgData = String((char)joinToken) + "?";
    sendMsg(req);
  }

  void onJoinMsg(Message& msg) {
    // JOIN_ACK: DataLen='2', MsgData=令牌(1) + 地址(1)
    if (msg.Function == F_JOIN_ACK && msg.DAddr == ADDR_NONE && msg.DataLen >= '2') {
      byte recvToken = (byte)msg.MsgData.charAt(0);
      if (recvToken != joinToken) return;
      byte a = (byte)msg.MsgData.charAt(1);
      if (a >= ADDR_FIRST && a <= ADDR_LAST) {
        myAddr = a;
        route[addrIdx(myAddr)].online = true;
        route[addrIdx(myAddr)].lastSeen = millis();
        markOnline(msg.SAddr);
        rapidBeaconCount = RAPID_BEACONS;
        lastHeartbeat = 0;
        setState(STATE_IN_NETWORK);
        Serial.print(F("[NET] Join "));
        Serial.println((char)myAddr);
        printNodeBanner();
      }
    }
  }

  void checkJoinTimeout() {
    if (joinTimer == 0) return;
    if (millis() - joinTimer < ACK_TIMEOUT) return;
    joinRetries++;
    if (joinRetries >= RETRY_MAX) {
      Serial.print(F("[NET] Join fail to "));
      Serial.println((char)joinTarget);
      startScan();
      return;
    }
    sendJoinReq();
    joinTimer = millis();
  }

  // ==================== 网络运行 ====================
  void onNetMsg(Message& msg) {
    // 地址冲突检测：听到了与我相同地址的节点
    if (msg.SAddr == myAddr && msg.Function != F_JOIN_REQ && msg.Function != F_JOIN_ACK) {
      Serial.print(F("[NET] Conflict "));
      Serial.println((char)myAddr);
      resetRoute();
      myAddr = ADDR_NONE;
      startScan();
      return;
    }
    // 任何消息 -> 源在线
    if (msg.SAddr >= ADDR_FIRST && msg.SAddr <= ADDR_LAST && msg.SAddr != myAddr)
      markOnline(msg.SAddr);

    // 心跳携带路由表 -> 间接学习
    if (msg.Function == F_HEARTBEAT) {
      heartbeatsReceived++;
      decodeRoute(msg.SAddr, msg.MsgData);
    }

    if (msg.Function == F_DATA || msg.Function == F_BCAST)
      packetsReceived++;
    if (msg.Function == F_DATA_ACK || msg.Function == F_LEAVE_ACK)
      acksReceived++;

    // 测试模式：收到 ACK 计数
    if (testMode && msg.Function == F_DATA_ACK && msg.SAddr == testTargetAddr)
      testAcksReceived++;

    switch (msg.Function) {
      case F_JOIN_REQ:  handleJoinReq(msg);  break;
      case F_LEAVE:     handleLeaveReq(msg); break;
      case F_DATA:      handleData(msg);     break;
      case F_BCAST:     handleBcast(msg);    break;
    }
  }

  void handleJoinReq(Message& msg) {
    if (countOnline() >= MAX_NODES - 1) return;
    byte na = pickUnusedAddr();
    if (na == ADDR_NONE) return;
    byte token = (byte)msg.MsgData.charAt(0);  // 回声请求中的令牌

    Message ack;
    ack.DAddr = ADDR_NONE;
    ack.SAddr = myAddr;
    ack.Function = F_JOIN_ACK;
    ack.DataLen = '2';                          // 令牌 + 地址
    ack.MsgData = String((char)token) + String((char)na);
    sendMsg(ack);
    markOnline(na);
    // 分配后立即发心跳，让网络其他节点尽快学习到新节点
    Message hb;
    hb.DAddr = ADDR_BCAST; hb.SAddr = myAddr;
    hb.Function = F_HEARTBEAT;
    String rt = encodeRoute();
    hb.DataLen = (byte)(rt.length() + '0'); hb.MsgData = rt;
    sendMsg(hb);
  }

  void handleLeaveReq(Message& msg) {
    markOffline(msg.SAddr);
    Message ack;
    ack.DAddr = msg.SAddr;
    ack.SAddr = myAddr;
    ack.Function = F_LEAVE_ACK;
    ack.DataLen = '1';
    ack.MsgData = " ";
    sendMsg(ack);
  }

  void handleData(Message& msg) {
    int rssi = LoRa.packetRssi();
    float snr = LoRa.packetSnr();
    Serial.print(F("[RX] <"));
    Serial.print((char)msg.SAddr);
    Serial.print(F(": "));
    Serial.print(msg.MsgData);
    Serial.print(F(" [RSSI "));
    Serial.print(rssi);
    Serial.print(F("dBm SNR "));
    Serial.print(snr, 1);
    Serial.println(F("dB]"));
    Message ack;
    ack.DAddr = msg.SAddr;
    ack.SAddr = myAddr;
    ack.Function = F_DATA_ACK;
    ack.DataLen = '1';
    ack.MsgData = " ";
    sendMsg(ack);
  }

  void handleBcast(Message& msg) {
    int rssi = LoRa.packetRssi();
    float snr = LoRa.packetSnr();
    Serial.print(F("[BCAST] <"));
    Serial.print((char)msg.SAddr);
    Serial.print(F(": "));
    Serial.print(msg.MsgData);
    Serial.print(F(" [RSSI "));
    Serial.print(rssi);
    Serial.print(F("dBm SNR "));
    Serial.print(snr, 1);
    Serial.println(F("dB]"));
  }

  // ----- 心跳 -----
  void doHeartbeat() {
    unsigned long iv = (rapidBeaconCount > 0) ? 200UL : HEARTBEAT_INTERVAL;
    if (millis() - lastHeartbeat < iv) return;
    lastHeartbeat = millis();

    Message hb;
    hb.DAddr = ADDR_BCAST;
    hb.SAddr = myAddr;
    hb.Function = F_HEARTBEAT;
    String rt = encodeRoute();
    hb.DataLen = (byte)(rt.length() + '0');
    hb.MsgData = rt;
    sendMsg(hb);

    if (rapidBeaconCount > 0) rapidBeaconCount--;
  }

  // ----- 超时 -----
  void checkTimeouts() {
    for (int i = 0; i < MAX_NODES; i++) {
      if (i == addrIdx(myAddr)) continue;
      if (!route[i].online) continue;
      if (millis() - route[i].lastSeen > NEIGHBOR_TIMEOUT)
        markOffline(idxAddr(i));
    }
  }

  // ==================== 退网 ====================
  void doLeave() {
    if (state != STATE_IN_NETWORK) return;
    Serial.println(F("[NET] Leave"));
    Message msg;
    msg.DAddr = ADDR_BCAST;
    msg.SAddr = myAddr;
    msg.Function = F_LEAVE;
    msg.DataLen = '1';
    msg.MsgData = " ";
    sendMsg(msg);
    resetRoute();
    myAddr = ADDR_NONE;
    leaveTimer = millis();
    setState(STATE_LEAVING);
  }

  void checkLeaveTimeout() {
    if (millis() - leaveTimer > LEAVE_TIMEOUT) {
      Serial.println(F("[NET] Left"));
      startScan();
    }
  }

  // ==================== 测试模式 ====================
  void handleTestMode() {
    if (state != STATE_IN_NETWORK) { testMode = false; return; }
    if (millis() - testLastSend < TEST_SEND_INTERVAL) return;
    testLastSend = millis();

    // 发送测试 ping
    Message m;
    m.DAddr = testTargetAddr;
    m.SAddr = myAddr;
    m.Function = F_DATA;
    m.DataLen = '1';
    m.MsgData = "t";
    sendMsg(m);
    testPacketsSent++;

    if (testPacketsSent >= testPacketsToSend) {
      testMode = false;
      unsigned long elapsed = millis() - testStartTime;
      Serial.println(F("[TEST] Done"));
      Serial.print(F("  Sent: ")); Serial.println(testPacketsSent);
      Serial.print(F("  ACK: ")); Serial.println(testAcksReceived);
      int loss = 100 - (testAcksReceived * 100 / testPacketsSent);
      Serial.print(F("  Loss: ")); Serial.print(loss); Serial.println(F("%"));
      Serial.print(F("  Time: ")); Serial.print(elapsed); Serial.println(F("ms"));
      if (testAcksReceived > 0) {
        Serial.print(F("  RTT: ~")); Serial.print(elapsed / testAcksReceived); Serial.println(F("ms"));
      }
    }
  }

  // ==================== 串口 ====================
  void processSerial() {
    if (Serial.available() <= 0) return;
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') return;

    switch (c) {
      case CMD_STATUS: printStatus(); break;
      case CMD_LEAVE:  doLeave(); break;
      case CMD_SEND: {
        String r = Serial.readStringUntil('\n');
        if (r.length() >= 2) {
          byte t = (byte)r.charAt(0);
          r.remove(0, 1);
          sendUnicast(t, r);
        }
        break;
      }
      case CMD_BCAST: {
        String r = Serial.readStringUntil('\n');
        sendBroadcast(r);
        break;
      }
      case CMD_TEST: {
        // T<target><n>  e.g. T3 = ping node3, T310 = ping node3 10 times
        String r = Serial.readStringUntil('\n');
        if (r.length() >= 1) {
          testTargetAddr = (byte)r.charAt(0);
          testPacketsToSend = 10;
          if (r.length() >= 2) {
            int n = r.substring(1).toInt();
            if (n > 0 && n <= 100) testPacketsToSend = n;
          }
          testPacketsSent = 0;
          testAcksReceived = 0;
          testLastSend = 0;
          testStartTime = millis();
          testMode = true;
          Serial.print(F("[TEST] Sending "));
          Serial.print(testPacketsToSend);
          Serial.print(F(" pings to "));
          Serial.println((char)testTargetAddr);
        }
        break;
      }
      case CMD_RESET_STATS: {
        resetStats();
        Serial.println(F("[STATS] Reset"));
        break;
      }
    }
  }

  void printNodeBanner() {
    Serial.println(F("========================"));
    Serial.print(F("*** NODE "));
    Serial.print((char)myAddr);
    Serial.println(F(" ***"));
    Serial.println(F("========================"));
  }

  void printStatus() {
    printNodeBanner();
    Serial.println(F("--- ROUTE ---"));
    for (int i = 0; i < MAX_NODES; i++) {
      Serial.print(F("  "));
      Serial.print((char)idxAddr(i));
      Serial.print(F(": "));
      if (i == addrIdx(myAddr)) { Serial.println(F("SELF")); continue; }
      if (!route[i].online) { Serial.println(F("--")); continue; }
      Serial.print(F("ON "));
      Serial.print((millis() - route[i].lastSeen) / 1000);
      Serial.println(F("s"));
    }

    // 网络质量
    Serial.println(F("=== STATS ==="));
    Serial.print(F("TX packets: ")); Serial.println(packetsSent);
    Serial.print(F("RX packets: ")); Serial.println(packetsReceived);
    Serial.print(F("HB sent: ")); Serial.println(heartbeatsSent);
    Serial.print(F("HB recv: ")); Serial.println(heartbeatsReceived);
    Serial.print(F("ACK sent: ")); Serial.println(acksSent);
    Serial.print(F("ACK recv: ")); Serial.println(acksReceived);
    Serial.print(F("CRC good: ")); Serial.println(rxGood);
    Serial.print(F("CRC bad: ")); Serial.println(rxBad);
    if (rssiSampleCount > 0) {
      int rssiAvg = (int)(rssiSum / rssiSampleCount);
      Serial.print(F("RSSI: "));
      Serial.print(rssiMin); Serial.print(F("/"));
      Serial.print(rssiAvg); Serial.print(F("/"));
      Serial.print(rssiMax); Serial.println(F(" dBm (min/avg/max)"));
    }
    if (snrSampleCount > 0) {
      long snrSum = 0;
      for (int i = 0; i < snrSampleCount; i++) snrSum += snrSamples[i];
      Serial.print(F("SNR: "));
      Serial.print((float)snrSum / (snrSampleCount * 10.0), 1);
      Serial.println(F(" dB (avg)"));
    }
    if (testMode) {
      Serial.print(F("Test: "));
      Serial.print(testPacketsSent); Serial.print(F(" sent, "));
      Serial.print(testAcksReceived); Serial.print(F(" acked, "));
      if (testPacketsSent > 0) {
        int loss = 100 - (testAcksReceived * 100 / testPacketsSent);
        Serial.print(loss); Serial.print(F("% loss"));
      }
      Serial.println();
    }
  }

  void sendUnicast(byte t, String d) {
    if (state != STATE_IN_NETWORK) { Serial.println(F("[ERR] Off")); return; }
    Message m;
    m.DAddr = t; m.SAddr = myAddr; m.Function = F_DATA;
    m.DataLen = (byte)(d.length() + '0'); m.MsgData = d;
    sendMsg(m);
    Serial.print(F("[TX] >")); Serial.print((char)t);
    Serial.print(F(": ")); Serial.println(d);
  }

  void sendBroadcast(String d) {
    if (state != STATE_IN_NETWORK) { Serial.println(F("[ERR] Off")); return; }
    Message m;
    m.DAddr = ADDR_BCAST; m.SAddr = myAddr; m.Function = F_BCAST;
    m.DataLen = (byte)(d.length() + '0'); m.MsgData = d;
    sendMsg(m);
    Serial.print(F("[BCAST] >")); Serial.println(d);
  }
};

#endif
