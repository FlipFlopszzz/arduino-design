#!/usr/bin/env python3
"""LoRa 自组网监控 — PySide6"""
import sys, re
from PySide6 import QtWidgets, QtCore, QtSerialPort
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtGui import QPainter, QColor, QPen


PANEL_COLORS = ["#00ff00", "#00ffff", "#ffff00", "#ff8800"]
PANEL_NAMES = ["节点A", "节点B", "节点C", "节点D"]


class SerialPanel(QtWidgets.QGroupBox):
    logSignal = QtCore.Signal(str, str)

    def __init__(self, name, idx):
        super().__init__(name)
        self._idx = idx
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
        self._uniTarget.addItems([str(i) for i in range(1, 21)])
        self._uniTarget.setEditable(True)
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
        self._pingTarget = QtWidgets.QComboBox()
        self._pingTarget.addItems([str(i) for i in range(1, 21)])
        self._pingTarget.setEditable(True)
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
        r4.addSpacing(8)
        self._clearBtn = QtWidgets.QPushButton("清屏")
        self._clearBtn.clicked.connect(self._clearLog)
        r4.addWidget(self._clearBtn)
        layout.addLayout(r4)

        # ── R5：本节点 RSSI 折线图 ──
        self._rssi_samples = []
        self._rssi_max = 20  # ~1min @3s 轮询

        self._rssi_series = QLineSeries()
        c = QColor(PANEL_COLORS[idx])
        c.setAlpha(200)
        self._rssi_series.setPen(QPen(c, 2))

        self._rssi_chart = QChart()
        self._rssi_chart.addSeries(self._rssi_series)
        self._rssi_chart.setTitle("RSSI (dBm)")
        self._rssi_chart.legend().hide()
        self._rssi_chart.setAnimationOptions(QChart.AnimationOptions.NoAnimation)
        self._rssi_chart.setBackgroundBrush(self.palette().window())
        self._rssi_chart.setPlotAreaBackgroundVisible(False)

        # 自适应主题：从 palette 取 label/grid 颜色
        txtColor = self.palette().color(self.palette().ColorRole.Text)
        txtColor.setAlpha(160)
        gridColor = self.palette().color(self.palette().ColorRole.Mid)
        gridColor.setAlpha(100)

        self._axis_x = QValueAxis()
        self._axis_x.setRange(0, self._rssi_max)
        self._axis_x.setVisible(False)
        self._rssi_chart.addAxis(self._axis_x, QtCore.Qt.Alignment.AlignBottom)
        self._rssi_series.attachAxis(self._axis_x)

        self._axis_y = QValueAxis()
        self._axis_y.setRange(-80, -10)
        self._axis_y.setLabelFormat("%d")
        self._axis_y.setLabelsColor(txtColor)
        self._axis_y.setGridLineColor(gridColor)
        self._axis_y.setTickCount(4)
        self._rssi_chart.addAxis(self._axis_y, QtCore.Qt.Alignment.AlignLeft)
        self._rssi_series.attachAxis(self._axis_y)

        self._rssi_view = QChartView(self._rssi_chart)
        self._rssi_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._rssi_view.setMinimumHeight(140)
        self._rssi_view.setMaximumHeight(160)
        layout.addWidget(self._rssi_view)

        # ── R6：日志框 ──
        self._logT = QtWidgets.QTextEdit()
        self._logT.setReadOnly(True)
        layout.addWidget(self._logT, stretch=1)

        self.setMinimumWidth(200)

    # ---------- 串口操作 ----------
    def _write(self, cmd):
        if self._serial.isOpen():
            self._log(f"[CMD] {cmd}")
            self._serial.write((cmd + "\n").encode())
            self._serial.waitForBytesWritten(300)

    def is_connected(self):
        return self._connected

    def send_broadcast_raw(self, msg):
        """供 MonitorWindow 轮询调用，不写日志"""
        if self._serial.isOpen():
            self._serial.write((f"B{msg}\n").encode())
            self._serial.waitForBytesWritten(100)

    def _sendUnicast(self):
        t = self._uniTarget.currentText()
        msg = self._uniMsg.text().strip()
        if msg:
            self._write(f"D{t} {msg}")
            self._uniMsg.clear()

    def _sendBroadcast(self):
        msg = self._bcastMsg.text().strip()
        if msg:
            self._write(f"B{msg}")
            self._bcastMsg.clear()

    def _sendPing(self):
        t = self._pingTarget.currentText().strip()
        try:
            n = int(self._pingCount.text())
        except ValueError:
            n = 10
        self._write(f"T{t} {n}")

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
                self._log("[DEBUG] 串口已连接")
            else:
                self._log(f"[ERR] 失败: {self._serial.errorString()}")
        else:
            self._serial.close()
            self._connected = False
            self._connBtn.setText("连接")
            self.setTitle(self._name)
            self._log("[DEBUG] 已断开")

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
            self._handeRssi(text)
            self.logSignal.emit(self._name, text)

    def _handeRssi(self, text):
        m = re.search(r"\[RSSI\s*(-?\d+)", text)
        if not m:
            return
        val = int(m.group(1))
        self._rssi_samples.append(val)
        if len(self._rssi_samples) > self._rssi_max:
            self._rssi_samples.pop(0)
        self._rssi_series.clear()
        for i, v in enumerate(self._rssi_samples):
            self._rssi_series.append(i, v)

    def _onErr(self, err):
        if err == QtSerialPort.QSerialPort.SerialPortError.ResourceError and self._connected:
            self._log("[DEBUG] 串口断开")

    def _log(self, msg):
        self._logT.append(msg)
        sb = self._logT.verticalScrollBar()
        sb.setValue(sb.maximum())

    def cleanup(self):
        if self._serial.isOpen():
            self._serial.close()
        self._connected = False

    def _clearLog(self):
        self._logT.clear()
        self._log("[DEBUG] 已清屏")
        self._rssi_samples.clear()
        self._rssi_series.clear()


class MonitorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LoRa 自组网监控")
        self.resize(1800, 850)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(3)

        # 上方：路由表（左半）+ 网络统计 + 停止轮询（右半）
        infoRow = QtWidgets.QHBoxLayout()
        self._routeText = QtWidgets.QTextEdit()
        self._routeText.setReadOnly(True)
        self._routeText.setMaximumHeight(100)
        self._routeText.setPlaceholderText("路由表")
        infoRow.addWidget(self._routeText, stretch=1)

        rightCol = QtWidgets.QHBoxLayout()
        rightCol.setSpacing(3)
        self._statsText = QtWidgets.QTextEdit()
        self._statsText.setReadOnly(True)
        self._statsText.setMaximumHeight(100)
        self._statsText.setPlaceholderText("网络统计")
        rightCol.addWidget(self._statsText, stretch=1)
        self._pollBtn = QtWidgets.QPushButton("停止 RSSI 轮询")
        self._pollBtn.setFixedHeight(100)
        self._pollBtn.setFixedWidth(110)
        self._pollBtn.clicked.connect(self._togglePoll)
        rightCol.addWidget(self._pollBtn)
        infoRow.addLayout(rightCol, stretch=1)
        layout.addLayout(infoRow)

        # 下部：四个节点面板（等分填满）
        panelsRow = QtWidgets.QHBoxLayout()
        panelsRow.setSpacing(3)
        self._panels = []
        for i, name in enumerate(PANEL_NAMES):
            p = SerialPanel(name, i)
            p.logSignal.connect(self._onPanelLog)
            panelsRow.addWidget(p, stretch=1)
            self._panels.append(p)
        layout.addLayout(panelsRow, stretch=1)

        self._statsMap = {}

        # ── RSSI 轮询定时器 ──
        self._poll_idx = 0
        self._poll_timer = QtCore.QTimer()
        self._poll_timer.timeout.connect(self._doPoll)
        self._poll_timer.start(3000)

    def _doPoll(self):
        """轮流向已连接的节点发广播，触发其他节点回传 RSSI"""
        for _ in range(len(self._panels)):
            p = self._panels[self._poll_idx]
            self._poll_idx = (self._poll_idx + 1) % len(self._panels)
            if p.is_connected():
                p.send_broadcast_raw("_")
                break

    def _togglePoll(self):
        if self._poll_timer.isActive():
            self._poll_timer.stop()
            self._pollBtn.setText("开始 RSSI 轮询")
        else:
            self._poll_timer.start(3000)
            self._pollBtn.setText("停止 RSSI 轮询")

    def _onPanelLog(self, name, text):
        s = text.strip()

        m = re.search(r"\*\*\* NODE (\d+)", text)
        if m:
            for p in self._panels:
                if p.title().startswith(name):
                    p.setTitle(f"{name} - N{m.group(1)}")
                    break

        if s == "--- ROUTE ---":
            self._routeText.clear()
            return
        m = re.match(r"^N(\d+): (ON|SELF)$", s)
        if m:
            self._routeText.append(f"N{m.group(1)}: {m.group(2)}")
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
        self._poll_timer.stop()
        for p in self._panels:
            p.cleanup()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = MonitorWindow()
    win.show()
    sys.exit(app.exec())
