"""Video feed display widget."""

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QPixmap
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
except ImportError:
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QPixmap
    ALIGN_CENTER = Qt.AlignCenter


class VideoWidget(QFrame):
    """Displays camera & vision detection video stream."""
    reset_node_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # Header bar
        header = QHBoxLayout()
        header.addWidget(QLabel("📹 LIVE VISION STREAM"))
        header.addStretch()

        btn_reset = QPushButton("🔄 Reset Node")
        btn_reset.setFixedHeight(22)
        btn_reset.setToolTip("Close and open detection node again")
        btn_reset.clicked.connect(self.reset_node_requested.emit)
        header.addWidget(btn_reset)

        self.lbl_fps = QLabel("0.0 FPS")
        self.lbl_fps.setStyleSheet("color: #22c55e; font-weight: bold; margin-left: 6px;")
        header.addWidget(self.lbl_fps)
        layout.addLayout(header)

        # Video canvas
        self.lbl_canvas = QLabel("Waiting for video stream...")
        self.lbl_canvas.setAlignment(ALIGN_CENTER)
        self.lbl_canvas.setMinimumSize(320, 240)
        self.lbl_canvas.setStyleSheet("background-color: #0b0f17; border-radius: 4px;")
        layout.addWidget(self.lbl_canvas, stretch=1)

    def set_frame(self, qimg, fps):
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(
            self.lbl_canvas.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_canvas.setPixmap(scaled)
        self.lbl_fps.setText(f"{fps:.1f} FPS")
