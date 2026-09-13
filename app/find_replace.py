"""
Find & Replace dialog with regex, case-sensitive, whole word, wrap options.
"""

import re
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QGroupBox,
)


class FindReplaceDialog(QDialog):
    def __init__(self, editor, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self._editor = editor
        self.setWindowTitle("Find & Replace")
        self.setMinimumWidth(440)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self._drag_pos = None
        self._build_ui()

    def _build_ui(self):
        # Master layout
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.setSpacing(0)

        # ── Custom Dialog Title Bar
        title_bar = QWidget()
        title_bar.setObjectName("DialogTitleBar")
        title_bar.setFixedHeight(32)
        title_bar.setStyleSheet("""
            QWidget#DialogTitleBar {
                background-color: #16161C;
                border-bottom: 1px solid #2D2D3F;
            }
        """)

        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(12, 0, 0, 0)
        tb_layout.setSpacing(0)

        title_lbl = QLabel("Find & Replace")
        title_lbl.setStyleSheet("color: #CCCCDD;")
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch(1)

        close_btn = QPushButton("\u00D7")
        close_btn.setFixedSize(36, 32)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8888A0;
            }
            QPushButton:hover {
                background-color: #C0392B;
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.close)
        tb_layout.addWidget(close_btn)

        master_layout.addWidget(title_bar)

        # ── Drag to move dialog handlers
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

        # ── Dialog body
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)
        master_layout.addWidget(body)

        # ── Input fields
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Find:"), 0, 0)
        self._find_edit = QLineEdit()
        self._find_edit.setPlaceholderText("Search text…")
        self._find_edit.returnPressed.connect(self._find_next)
        grid.addWidget(self._find_edit, 0, 1)

        grid.addWidget(QLabel("Replace:"), 1, 0)
        self._replace_edit = QLineEdit()
        self._replace_edit.setPlaceholderText("Replacement text…")
        grid.addWidget(self._replace_edit, 1, 1)

        layout.addLayout(grid)

        # ── Options
        opts_box = QGroupBox("Options")
        opts_layout = QHBoxLayout(opts_box)
        opts_layout.setSpacing(16)

        self._case_cb = QCheckBox("Match &Case")
        self._whole_cb = QCheckBox("Whole &Word")
        self._regex_cb = QCheckBox("Re&gex")
        self._wrap_cb = QCheckBox("&Wrap Around")
        self._wrap_cb.setChecked(True)

        for w in (self._case_cb, self._whole_cb, self._regex_cb, self._wrap_cb):
            opts_layout.addWidget(w)
        opts_layout.addStretch()

        layout.addWidget(opts_box)

        # ── Status label
        self._status = QLabel("")
        self._status.setStyleSheet("color: #888899;")
        layout.addWidget(self._status)

        # ── Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._btn_prev = QPushButton("◀  Previous")
        self._btn_next = QPushButton("Next  ▶")
        self._btn_replace = QPushButton("Replace")
        self._btn_replace_all = QPushButton("Replace All")
        self._btn_close = QPushButton("Close")

        self._btn_next.setDefault(True)

        for btn in (self._btn_prev, self._btn_next, self._btn_replace,
                    self._btn_replace_all, self._btn_close):
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

        # ── Connections
        self._btn_next.clicked.connect(self._find_next)
        self._btn_prev.clicked.connect(self._find_prev)
        self._btn_replace.clicked.connect(self._replace_once)
        self._btn_replace_all.clicked.connect(self._replace_all)
        self._btn_close.clicked.connect(self.close)
        self._find_edit.textChanged.connect(lambda _: self._status.setText(""))

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _build_flags(self) -> re.RegexFlag:
        flags = re.MULTILINE
        if not self._case_cb.isChecked():
            flags |= re.IGNORECASE
        return flags

    def _make_pattern(self, text: str) -> re.Pattern | None:
        if not text:
            return None
        try:
            if self._regex_cb.isChecked():
                pat = text
            else:
                pat = re.escape(text)
            if self._whole_cb.isChecked():
                pat = r"\b" + pat + r"\b"
            return re.compile(pat, self._build_flags())
        except re.error as e:
            self._status.setText(f"Regex error: {e}")
            return None

    def _get_text(self) -> str:
        return self._editor.toPlainText()

    def _set_selection(self, start: int, end: int):
        cur = self._editor.textCursor()
        cur.setPosition(start)
        cur.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self._editor.setTextCursor(cur)
        self._editor.ensureCursorVisible()

    def _current_pos(self) -> int:
        cur = self._editor.textCursor()
        start = cur.selectionStart()
        end = cur.selectionEnd()
        return end if end > start else cur.position()

    def _find_next(self):
        pattern = self._make_pattern(self._find_edit.text())
        if not pattern:
            return
        text = self._get_text()
        pos = self._current_pos()
        m = pattern.search(text, pos)
        if m is None and self._wrap_cb.isChecked():
            m = pattern.search(text, 0)
        if m:
            self._set_selection(m.start(), m.end())
            self._status.setText("")
        else:
            self._status.setText("No matches found.")

    def _find_prev(self):
        pattern = self._make_pattern(self._find_edit.text())
        if not pattern:
            return
        text = self._get_text()
        cur = self._editor.textCursor()
        pos = cur.selectionStart()
        matches = list(pattern.finditer(text, 0, pos))
        if not matches and self._wrap_cb.isChecked():
            matches = list(pattern.finditer(text))
        if matches:
            m = matches[-1]
            self._set_selection(m.start(), m.end())
            self._status.setText("")
        else:
            self._status.setText("No matches found.")

    def _replace_once(self):
        pattern = self._make_pattern(self._find_edit.text())
        if not pattern:
            return
        cur = self._editor.textCursor()
        selected = cur.selectedText()
        text = self._get_text()
        pos = cur.selectionStart()
        end_pos = cur.selectionEnd()
        # Check if current selection is a match
        if selected and pattern.fullmatch(selected):
            replacement = pattern.sub(self._replace_edit.text(), selected, count=1)
            cur.insertText(replacement)
        self._find_next()

    def _replace_all(self):
        pattern = self._make_pattern(self._find_edit.text())
        if not pattern:
            return
        text = self._get_text()
        new_text, count = pattern.subn(self._replace_edit.text(), text)
        if count:
            cur = self._editor.textCursor()
            cur.select(QTextCursor.SelectionType.Document)
            cur.insertText(new_text)
            self._status.setText(f"Replaced {count} occurrence(s).")
        else:
            self._status.setText("No matches found.")

    # ── Public API ───────────────────────────────────────────────────────────

    def set_search_term(self, text: str):
        self._find_edit.setText(text)
        self._find_edit.selectAll()

    def show_and_focus(self):
        self.show()
        self.raise_()
        self._find_edit.setFocus()
        self._find_edit.selectAll()
