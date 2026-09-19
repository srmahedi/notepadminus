from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QSpinBox, QWidget, QComboBox, QRadioButton,
    QButtonGroup, QFrame, QScrollArea
)

class _FramelessDialog(QDialog):
    def __init__(self, parent=None, title=""):
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self._drag_pos = None
        self._title = title
        
    def _setup_header(self, layout):
        title_bar = QWidget()
        title_bar.setObjectName("DialogTitleBar")
        title_bar.setFixedHeight(32)
        title_bar.setStyleSheet("""
            QWidget#DialogTitleBar {
                background-color: #252526;
                border-bottom: 1px solid #3C3C3C;
            }
        """)

        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(12, 0, 0, 0)
        tb_layout.setSpacing(0)

        title_lbl = QLabel(self._title)
        title_lbl.setStyleSheet("color: #CCCCCC;")
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch(1)

        close_btn = QPushButton("\u00D7")
        close_btn.setFixedSize(36, 32)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #858585;
            }
            QPushButton:hover {
                background-color: #3C3C3C;
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.reject)
        tb_layout.addWidget(close_btn)

        layout.addWidget(title_bar)

        # Drag handlers
        def tb_mousePress(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

        def tb_mouseMove(event):
            if (event.buttons() & Qt.MouseButton.LeftButton) and self._drag_pos is not None:
                self.move(event.globalPosition().toPoint() - self._drag_pos)

        def tb_mouseRelease(event):
            self._drag_pos = None

        title_bar.mousePressEvent = tb_mousePress
        title_bar.mouseMoveEvent = tb_mouseMove
        title_bar.mouseReleaseEvent = tb_mouseRelease

class DarkMessageBox(_FramelessDialog):
    def __init__(self, parent=None, title="", text="", buttons=None, icon_color="#858585"):
        super().__init__(parent, title)
        self.setMinimumWidth(380)
        
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.setSpacing(0)
        
        self._setup_header(master_layout)
        
        body = QWidget()
        body.setStyleSheet("background-color: #252526; border: 1px solid #3C3C3C; border-top: none;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 20, 20, 16)
        body_layout.setSpacing(16)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        # Icon
        self.icon_lbl = QLabel("ℹ")
        self.icon_lbl.setStyleSheet(f"color: {icon_color};")
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.addWidget(self.icon_lbl)
        
        # Text
        self.text_lbl = QLabel(text)
        self.text_lbl.setStyleSheet("color: #CCCCCC;")
        self.text_lbl.setWordWrap(True)
        content_layout.addWidget(self.text_lbl, 1)
        
        body_layout.addLayout(content_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch(1)
        
        self.result_button = None
        
        if buttons is None:
            buttons = [("OK", QDialog.DialogCode.Accepted, True)]
            
        for text, code, is_default in buttons:
            btn = QPushButton(text)
            if is_default:
                btn.setDefault(True)
            btn.setStyleSheet(_BUTTON_STYLE)
            btn.clicked.connect(lambda checked=False, c=code: self.finish_dialog(c))
            btn_layout.addWidget(btn)
            
        body_layout.addLayout(btn_layout)
        master_layout.addWidget(body)
        
    def finish_dialog(self, code):
        self.result_button = code
        self.done(code)
        
    @classmethod
    def question(cls, parent, title, text):
        dialog = cls(
            parent, title, text,
            buttons=[
                ("Save", 1, True),
                ("Don't Save", 2, False),
                ("Cancel", 0, False)
            ],
            icon_color="#858585"
        )
        dialog.exec()
        return dialog.result_button
        
    @classmethod
    def critical(cls, parent, title, text):
        dialog = cls(
            parent, title, text,
            buttons=[("OK", 1, True)],
            icon_color="#858585"
        )
        dialog.exec()
        
    @classmethod
    def about(cls, parent, title, html_text):
        dialog = cls(
            parent, title, "",
            buttons=[("Close", 1, True)],
            icon_color="#858585"
        )
        # Use HTML for text label
        dialog.text_lbl.setText(html_text)
        dialog.exec()

class DarkInputDialog(_FramelessDialog):
    def __init__(self, parent=None, title="", label_text="", value=1, min_val=1, max_val=100):
        super().__init__(parent, title)
        self.setMinimumWidth(320)
        
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.setSpacing(0)
        
        self._setup_header(master_layout)
        
        body = QWidget()
        body.setStyleSheet("background-color: #252526; border: 1px solid #3C3C3C; border-top: none;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 20, 20, 16)
        body_layout.setSpacing(12)
        
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #CCCCCC;")
        body_layout.addWidget(lbl)
        
        self.spin = QSpinBox()
        self.spin.setRange(min_val, max_val)
        self.spin.setValue(value)
        self.spin.setStyleSheet(_INPUT_STYLE)
        body_layout.addWidget(self.spin)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch(1)
        
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet(_BUTTON_STYLE)
        ok_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(_BUTTON_STYLE)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        body_layout.addLayout(btn_layout)
        
        master_layout.addWidget(body)
        
    @classmethod
    def getInt(cls, parent, title, label_text, value, min_val, max_val):
        dialog = cls(parent, title, label_text, value, min_val, max_val)
        res = dialog.exec()
        return dialog.spin.value(), (res == QDialog.DialogCode.Accepted)


_INPUT_STYLE = """
    QLineEdit, QSpinBox, QComboBox {
        background-color: #3C3C3C;
        border: 1px solid #3C3C3C;
        border-radius: 5px;
        padding: 6px 10px;
        color: #CCCCCC;
    }
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
        border-color: #3C3C3C;
    }
    QComboBox::drop-down {
        border: none;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid #858585;
        margin-right: 5px;
    }
"""

_BUTTON_STYLE = """
    QPushButton {
        background-color: #3C3C3C;
        border: 1px solid #3C3C3C;
        border-radius: 5px;
        padding: 8px 16px;
        color: #CCCCCC;
        min-width: 80px;
    }
    QPushButton:hover {
        background-color: #454545;
        border-color: #454545;
    }
    QPushButton:pressed {
        background-color: #2D2D30;
    }
    QPushButton:default {
        background-color: #3C3C3C;
        border-color: #3C3C3C;
    }
    QPushButton:default:hover {
        background-color: #454545;
    }
"""

_RADIO_STYLE = """
    QRadioButton {
        color: #CCCCCC;
        spacing: 8px;
    }
    QRadioButton::indicator {
        width: 16px;
        height: 16px;
        border: 2px solid #858585;
        border-radius: 8px;
        background-color: #3C3C3C;
    }
    QRadioButton::indicator:checked {
        background-color: #3C3C3C;
        border-color: #3C3C3C;
    }
    QRadioButton::indicator:hover {
        border-color: #858585;
    }
"""



