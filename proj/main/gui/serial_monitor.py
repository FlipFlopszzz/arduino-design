#!/usr/bin/env python3
"""LoRa 四节点自组网监控 — PySide6"""
import sys, re
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
        layout.setContentsMargins(3, 3, 3, 3)

        # ── R1：COM口 + 连接 ──
        r1 = QtWidgets.QHBoxLayout()
        r1.setSpacing(3)
        self._portCb = QtWidgets.QComboBox()
        self._portCb.setEditable(True)
        for info in QtSerialPort.QSerialPortInfo.availablePorts():
            self._portCb.addItem(info.portName())
        self._connBtn = QtWidgets.QPushButton("连接")
        self._connBtn.clicked.connect(self._toggleConn)
        r1.addWidget(self._portCb, stretch=1)
        r1.addWidget(self._connBtn)
        layout.addLayout(r1)

        # ── R2：单播 ──
        r2 = QtWidgets.QHBoxLayout()
        r2.setSpacing(3)
        self._uniTarget = QtWidgets.QComboBox()
        self._uniTarget.addItems(["1", "2", "3", "4"])
        self._uniTarget.setFixedWidth(60)
        self._uniMsg = QtWidgets.QLineEdit()
        self._uniMsg.setPlaceholderText("消息")
        self._uniBtn = QtWidgets.QPushButton("单播")
        self._uniBtn.clicked.connect(self._sendUnicast)
        self._uniMsg.returnPressed.connect(self._sendUnicast)
        r2.addWidget(self._uniTarget)
        r2.addWidget(self._uniMsg, stretch=1)
        r2.addWidget(self._uniBtn)
        layout.addLayout(r2)

        # ── R3：广播 ──
        r3 = QtWidgets.QHBoxLayout()
        r3.setSpacing(3)
        self._bcastMsg = QtWidgets.QLineEdit()
        self._bcastMsg.setPlaceholderText("广播消息")
        self._bcastBtn = QtWidgets.QPushButton("广播")
        self._bcastBtn.clicked.connect(self._sendBroadcast)
        self._bcastMsg.returnPressed.connect(self._sendBroadcast)
        r3.addWidget(self._bcastMsg, stretch=1)
        r3.addWidget(self._bcastBtn)
        layout.addLayout(r3)

        # ── R4：Ping + 快捷按钮 ──
        r4 = QtWidgets.QHBoxLayout()
        r4.setSpacing(3)
        r4.addWidget(QtWidgets.QLabel("Ping→"))
        self._pingTarget = QtWidgets.QComboBox()
        self._pingTarget.addItems(["1", "2", "3", "4"])
        self._pingTarget.setFixedWidth(60)
        self._pingCount = QtWidgets.QLineEdit()
        self._pingCount.setText("10")
        self._pingCount.setFixedWidth(60)
        r4.addWidget(self._pingTarget)
        r4.addWidget(self._pingCount)
        r4.addWidget(QtWidgets.QLabel("次"))
        r4.addSpacing(4)
        self._pingBtn = QtWidgets.QPushButton("Ping")
        self._pingBtn.clicked.connect(self._sendPing)
        r4.addWidget(self._pingBtn)
        r4.addSpacing(4)
        self._statusBtn = QtWidgets.QPushButton("状态(S)")
        self._statusBtn.clicked.connect(lambda: self._write("S"))
        self._leaveBtn = QtWidgets.QPushButton("退网(L)")
        self._leaveBtn.clicked.connect(lambda: self._write("L"))
        self._resetBtn = QtWidgets.QPushButton("重置(R)")
        self._resetBtn.clicked.connect(lambda: self._write("R"))
        r4.addWidget(self._statusBtn)
        r4.addWidget(self._leaveBtn)
        r4.addWidget(self._resetBtn)
        layout.addLayout(r4)

        # 日志框
        self._logT = QtWidgets.QTextEdit()
        self._logT.setReadOnly(True)
        self._logT.setStyleSheet("font-family: Consolas; font-size: 10px;")
        layout.addWidget(self._logT, stretch=1)

        self.setMinimumWidth(200)

    # ---------- 串口操作 ----------
    def _write(self, cmd):
        if self._serial.isOpen():
            self._log(f"[CMD] {cmd}")
            self._serial.write((cmd + "\n").encode())
            self._serial.waitForBytesWritten(300)

    def _sendUnicast(self):
        t = self._uniTarget.currentText()
        msg = self._uniMsg.text().strip()
        if msg:
            self._write(f"D{t}{msg}")
            self._uniMsg.clear()

    def _sendBroadcast(self):
        msg = self._bcastMsg.text().strip()
        if msg:
            self._write(f"B{msg}")
            self._bcastMsg.clear()

    def _sendPing(self):
        t = self._pingTarget.currentText()
        try:
            n = int(self._pingCount.text())
        except ValueError:
            n = 10
        self._write(f"T{t}{n}")

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
                self._serial.setDataTerminalReady(False)
                QtCore.QThread.msleep(300)
                self._serial.clear()
                self._buf = b""
                self._connected = True
                self._connBtn.setText("断开")
                self._log("[SYS] 串口已连接")
            else:
                self._log(f"[ERR] 失败: {self._serial.errorString()}")
        else:
            self._serial.close()
            self._connected = False
            self._connBtn.setText("连接")
            self.setTitle(self._name)
            self._log("[SYS] 已断开")

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
            self._log(text)
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
        self.resize(1800, 750)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(3)

        # 上方：路由表 + 网络统计
        infoRow = QtWidgets.QHBoxLayout()
        self._routeText = QtWidgets.QTextEdit()
        self._routeText.setReadOnly(True)
        self._routeText.setMaximumHeight(120)
        self._routeText.setPlaceholderText("路由表")
        self._statsText = QtWidgets.QTextEdit()
        self._statsText.setReadOnly(True)
        self._statsText.setMaximumHeight(120)
        self._statsText.setPlaceholderText("网络统计")
        infoRow.addWidget(self._routeText)
        infoRow.addWidget(self._statsText)
        layout.addLayout(infoRow)

        # 四个节点面板（等分填满）
        panelsRow = QtWidgets.QHBoxLayout()
        panelsRow.setSpacing(3)
        self._panels = []
        for name in ("节点A", "节点B", "节点C", "节点D"):
            p = SerialPanel(name)
            p.logSignal.connect(self._onPanelLog)
            panelsRow.addWidget(p, stretch=1)
            self._panels.append(p)
        layout.addLayout(panelsRow, stretch=1)

        self._statsMap = {}

    def _onPanelLog(self, name, text):
        s = text.strip()

        if "*** NODE" in text:
            rest = text[text.find("*** NODE") + 9:]
            for c in rest:
                if c.isdigit():
                    for p in self._panels:
                        if p.title().startswith(name):
                            p.setTitle(f"{name} - N{c}")
                            break
                    break

        if s == "--- ROUTE ---":
            self._routeText.clear()
            return
        m = re.match(r"^(\d): (ON|SELF)$", s)
        if m:
            self._routeText.append(f"{m.group(1)}: ON")
            return

        if s.startswith("[") and "]" in s:
            s = s.split("]", 1)[1].strip()
        for kw in ["TX packets", "RX packets", "HB sent", "HB recv",
                   "ACK sent", "ACK recv", "CRC good", "CRC bad",
                   "RSSI", "SNR"]:
            if s.startswith(kw):
                self._statsMap[kw] = s
                self._updateStats()
                break

    def _updateStats(self):
        self._statsText.clear()
        keys = ["TX packets", "RX packets", "HB sent", "HB recv",
                "ACK sent", "ACK recv", "CRC good", "CRC bad",
                "RSSI", "SNR"]
        out = [self._statsMap[k] for k in keys if k in self._statsMap]
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
