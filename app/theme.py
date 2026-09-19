"""
Dark theme stylesheet for Notepad Minus.
"""

DARK_THEME = """
/* ── Global ──────────────────────────────────────────────── */
* {
    color: #CCCCCC;
    outline: none;
}

QWidget {
    background-color: #1E1E1E;
    color: #CCCCCC;
}

/* ── Menu Bar ─────────────────────────────────────────────── */
QMenuBar {
    background-color: #252526;
    border-bottom: 1px solid #3C3C3C;
    padding: 2px 4px;
    spacing: 2px;
}

QMenuBar::item {
    background: transparent;
    padding: 5px 10px;
    border-radius: 3px;
    color: #CCCCCC;
}

QMenuBar::item:selected,
QMenuBar::item:pressed {
    background-color: #3C3C3C;
    color: #FFFFFF;
}

QMenu {
    background-color: #252526;
    border: 1px solid #454545;
    border-radius: 6px;
    padding: 4px 0px;
}

QMenu::item {
    padding: 7px 28px 7px 16px;
    border-radius: 3px;
    margin: 1px 4px;
    color: #CCCCCC;
}

QMenu::item:selected {
    background-color: #3C3C3C;
    color: #FFFFFF;
}

QMenu::item:disabled {
    color: #858585;
}

QMenu::separator {
    height: 1px;
    background: #454545;
    margin: 4px 10px;
}

QMenu::indicator {
    width: 14px;
    height: 14px;
    margin-left: 4px;
}

/* ── Tool Bar ─────────────────────────────────────────────── */
QToolBar {
    background-color: #252526;
    border-bottom: 1px solid #3C3C3C;
    padding: 3px 6px;
    spacing: 2px;
}

QToolBar::separator {
    width: 1px;
    background: #454545;
    margin: 3px 4px;
}

QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 5px 7px;
    color: #CCCCCC;
}

QToolButton:hover {
    background-color: #3C3C3C;
    border-color: #454545;
    color: #FFFFFF;
}

QToolButton:pressed {
    background-color: #2D2D30;
}

QToolButton:checked {
    background-color: #3C3C3C;
    border-color: #3C3C3C;
    color: #FFFFFF;
}

/* ── Status Bar ───────────────────────────────────────────── */
QStatusBar {
    background-color: #3C3C3C;
    border-top: 1px solid #3C3C3C;
    color: #CCCCCC;
    padding: 2px 8px;
}

QStatusBar::item {
    border: none;
}

QStatusBar QLabel {
    color: #CCCCCC;
    padding: 0 8px;
}

/* ── Main Editor ──────────────────────────────────────────── */
QPlainTextEdit, QTextEdit {
    background-color: #1E1E1E;
    color: #CCCCCC;
    border: none;
    selection-background-color: #3C3C3C;
    selection-color: #FFFFFF;
    line-height: 1.6;
    padding: 8px 4px;
}

/* ── Scrollbars ───────────────────────────────────────────── */
QScrollBar:vertical {
    background: #1E1E1E;
    width: 14px;
    margin: 0px;
    border-radius: 0px;
    border: none;
}

QScrollBar::handle:vertical {
    background: #424242;
    min-height: 30px;
    border-radius: 0px;
    margin: 0px;
    border: none;
}

QScrollBar::handle:vertical:hover {
    background: #4E4E4E;
}

QScrollBar::handle:vertical:pressed {
    background: #555555;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background: #1E1E1E;
    height: 14px;
    margin: 0px;
    border-radius: 0px;
    border: none;
}

QScrollBar::handle:horizontal {
    background: #424242;
    min-width: 30px;
    border-radius: 0px;
    margin: 0px;
    border: none;
}

QScrollBar::handle:horizontal:hover {
    background: #4E4E4E;
}

QScrollBar::handle:horizontal:pressed {
    background: #555555;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* ── Dialogs ──────────────────────────────────────────────── */
QDialog {
    background-color: #252526;
    border: 1px solid #454545;
    border-radius: 6px;
}

QLabel {
    color: #CCCCCC;
    background: transparent;
}

QLineEdit {
    background-color: #3C3C3C;
    border: 1px solid #3C3C3C;
    border-radius: 2px;
    padding: 6px 10px;
    color: #CCCCCC;
    selection-background-color: #3C3C3C;
}

QLineEdit:focus {
    border-color: #3C3C3C;
    background-color: #3C3C3C;
}

QPushButton {
    background-color: #3C3C3C;
    border: 1px solid #3C3C3C;
    border-radius: 2px;
    padding: 7px 16px;
    color: #CCCCCC;
}

QPushButton:hover {
    background-color: #454545;
    border-color: #454545;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #2D2D30;
}

QPushButton:default {
    background-color: #3C3C3C;
    border-color: #3C3C3C;
    color: #FFFFFF;
}

QPushButton:default:hover {
    background-color: #454545;
}

QPushButton:disabled {
    background-color: #2D2D30;
    border-color: #2D2D30;
    color: #858585;
}

QCheckBox {
    color: #CCCCCC;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #858585;
    border-radius: 2px;
    background: #3C3C3C;
}

QCheckBox::indicator:checked {
    background: #3C3C3C;
    border-color: #3C3C3C;
}

QCheckBox::indicator:hover {
    border-color: #858585;
}

QComboBox {
    background-color: #3C3C3C;
    border: 1px solid #3C3C3C;
    border-radius: 2px;
    padding: 5px 10px;
    color: #CCCCCC;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #252526;
    border: 1px solid #454545;
    selection-background-color: #3C3C3C;
    color: #CCCCCC;
}

/* ── Splitter ─────────────────────────────────────────────── */
QSplitter::handle {
    background: #3C3C3C;
}

/* ── Tab Widget ───────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #3C3C3C;
    background: #1E1E1E;
}

QTabBar::tab {
    background: #2D2D30;
    border: 1px solid #3C3C3C;
    padding: 6px 14px;
    color: #858585;
    border-bottom: none;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
}

QTabBar::tab:selected {
    background: #1E1E1E;
    color: #CCCCCC;
    border-color: #3C3C3C;
}

/* ── Spin Box ─────────────────────────────────────────────── */
QSpinBox {
    background-color: #3C3C3C;
    border: 1px solid #3C3C3C;
    border-radius: 2px;
    padding: 5px 8px;
    color: #CCCCCC;
}

QSpinBox::up-button, QSpinBox::down-button {
    background: #3C3C3C;
    border: none;
    width: 16px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #454545;
}

/* ── Tooltip ──────────────────────────────────────────────── */
QToolTip {
    background-color: #252526;
    border: 1px solid #454545;
    color: #CCCCCC;
    padding: 5px 8px;
    border-radius: 4px;
}
"""


TITLE_BAR_STYLE = """
QWidget#TitleBar {
    background-color: #3C3C3C;
    border-bottom: 1px solid #3C3C3C;
}
"""
