#!/usr/bin/env python3
"""LoRa 四节点自组网监控 — PySide6"""

import sys
from PySide6 import QtWidgets, QtCore, QtSerialPort


class SerialPanel(QtWidgets.QGroupBox):
    logSignal = QtCore.Signal(str, str)

    def __init__(self, name):
        super().__init__(name)
        self._name = name
        self._serial = QtSerialPort.QSerialPort()
        self._serial.readyRead.connect(self._onRead)
        self._serial.errorOccurred.connect(self._onErr)
        self._buf = b""
        self._connected = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)

        # 第一行：COM口 + 连接按钮
        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(4)
        self._portCb = QtWidgets.QComboBox()
        self._portCb.setEditable(True)
        # 扫描真实串口
        for info in QtSerialPort.QSerialPortInfo.availablePorts():
            self._portCb.addItem(info.portName())
        self._connBtn = QtWidgets.QPushButton("连接")
        self._connBtn.clicked.connect(self._toggleConn)
        row1.addWidget(self._portCb, stretch=1)
        row1.addWidget(self._connBtn)
        layout.addLayout(row1)

        # 第二行：命令输入 + 发送按钮
        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(4)
        self._cmdE = QtWidgets.QLineEdit()
        self._cmdE.setPlaceholderText("命令")
        self._cmdE.returnPressed.connect(self._sendCmd)
        self._sendBtn = QtWidgets.QPushButton("发送")
        self._sendBtn.clicked.connect(self._sendCmd)
        row2.addWidget(self._cmdE)
        row2.addWidget(self._sendBtn)
        layout.addLayout(row2)

        # 第三行：日志输出框（填满剩余空间）
        self._logT = QtWidgets.QTextEdit()
        self._logT.setReadOnly(True)
        layout.addWidget(self._logT, stretch=1)

    def _toggleConn(self):
        if not self._connected:
            port = self._portCb.currentText().strip()
            self._serial.setPortName(port)
            self._serial.setBaudRate(9600)
            self._serial.setDataBits(QtSerialPort.QSerialPort.DataBits.Data8)
            self._serial.setParity(QtSerialPort.QSerialPort.Parity.NoParity)
            self._serial.setStopBits(QtSerialPort.QSerialPort.StopBits.OneStop)
            self._serial.setFlowControl(QtSerialPort.QSerialPort.FlowControl.NoFlowControl)
            if self._serial.open(QtCore.QIODevice.OpenModeFlag.ReadWrite):
                # 禁用 DTR 防止 Arduino 复位
                self._serial.setDataTerminalReady(False)
                QtCore.QThread.msleep(300)
                self._serial.clear()
                self._buf = b""
                self._connected = True
                self._connBtn.setText("断开")
                self._log("[SYS] 串口已连接")
            else:
                self._log(f"[ERR] 连接失败: {self._serial.errorString()}")
        else:
            self._serial.close()
            self._connected = False
            self._connBtn.setText("连接")
            self.setTitle(self._name)
            self._log("[SYS] 串口已断开")

    def _sendCmd(self):
        cmd = self._cmdE.text().strip()
        if cmd and self._serial.isOpen():
            self._log(f"[CMD] {cmd}")
            self._serial.write((cmd + "\n").encode())
            self._serial.waitForBytesWritten(500)
            self._cmdE.clear()

    def _onRead(self):
        raw = self._serial.readAll().data()
        self._buf += raw
        while b"\n" in self._buf:
            line, self._buf = self._buf.split(b"\n", 1)
            line = line.strip(b"\r").strip()
            if not line:
                continue
            try:
                text = line.decode("utf-8", errors="replace")
            except:
                continue
            # 显示到本面板日志
            self._log(text)
            # 发送给主窗口解析
            self.logSignal.emit(self._name, text)

    def _onErr(self, err):
        if err == QtSerialPort.QSerialPort.SerialPortError.ResourceError and self._connected:
            self._log("[SYS] 串口断开")

    def _log(self, msg):
        self._logT.append(msg)
        sb = self._logT.verticalScrollBar()
        sb.setValue(sb.maximum())

    def cleanup(self):
        if self._serial.isOpen():
            self._serial.close()
        self._connected = False


class MonitorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LoRa 自组网监控")
        self.resize(1100, 650)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(4)

        # 上方：路由表 + 网络统计（并排）
        infoRow = QtWidgets.QHBoxLayout()
        self._routeText = QtWidgets.QTextEdit()
        self._routeText.setReadOnly(True)
        self._routeText.setMaximumHeight(150)
        self._routeText.setPlaceholderText("路由表")
        self._statsText = QtWidgets.QTextEdit()
        self._statsText.setReadOnly(True)
        self._statsText.setMaximumHeight(150)
        self._statsText.setPlaceholderText("网络统计")
        infoRow.addWidget(self._routeText)
        infoRow.addWidget(self._statsText)
        layout.addLayout(infoRow)

        # 中间：四个节点面板
        panelsRow = QtWidgets.QHBoxLayout()
        self._panels = []
        for name in ("节点A", "节点B", "节点C", "节点D"):
            p = SerialPanel(name)
            p.logSignal.connect(self._onPanelLog)
            panelsRow.addWidget(p)
            self._panels.append(p)
        layout.addLayout(panelsRow, stretch=1)

        # 状态缓存
        self._nodeAddrs = {}         # panel_name -> node_addr
        self._onlineNodes = set()    # all online node addresses
        self._statsMap = {}

    def _onPanelLog(self, name, text):
        s = text.strip()

        # 解析当前面板的节点地址并更新标题
        m = text.find("*** NODE")
        if m >= 0:
            rest = text[m+9:]
            for c in rest:
                if c.isdigit():
                    self._nodeAddrs[name] = c
                    for p in self._panels:
                        if p.title().startswith(name):
                            p.setTitle(f"{name} - Node {c}")
                            break
                    break

        # 从路由表（X: ON 行）提取所有在线节点
        if ": ON" in s or ": SELF" in s:
            addr = s[0]
            if addr.isdigit():
                self._onlineNodes.add(addr)
                self._updateRoute()

        # 统计：去掉行头的 [节点X] 前缀
        if s.startswith("[") and "]" in s:
            s = s.split("]", 1)[1].strip()
        for kw in ["TX packets", "RX packets", "HB sent", "HB recv",
                   "ACK sent", "ACK recv", "CRC good", "CRC bad",
                   "RSSI", "SNR"]:
            if s.startswith(kw):
                self._statsMap[kw] = s
                self._updateStats()
                break

    def _updateRoute(self):
        self._routeText.clear()
        lines = []
        # 先显示已映射到面板的节点
        for name, addr in sorted(self._nodeAddrs.items()):
            lines.append(f"{name}: Node {addr}")
        # 再显示未映射的在线节点
        mapped = set(self._nodeAddrs.values())
        for addr in sorted(self._onlineNodes):
            if addr not in mapped:
                lines.append(f"Node {addr}: ON")
        if lines:
            self._routeText.append("\n".join(lines))

    def _updateStats(self):
        self._statsText.clear()
        keys = ["TX packets", "RX packets", "HB sent", "HB recv",
                "ACK sent", "ACK recv", "CRC good", "CRC bad",
                "RSSI", "SNR"]
        out = []
        for k in keys:
            if k in self._statsMap:
                out.append(self._statsMap[k])
        if out:
            self._statsText.append("\n".join(out))

    def closeEvent(self, event):
        for p in self._panels:
            p.cleanup()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = MonitorWindow()
    win.show()
    sys.exit(app.exec())
