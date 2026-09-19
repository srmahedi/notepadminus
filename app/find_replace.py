"""
Find & Replace dialog with regex, case-sensitive, whole word, wrap options.
VS Code-style widget positioned at top of editor.
"""

import re
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QTextCursor, QTextDocument, QKeySequence
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QToolButton,
)


class FindReplaceDialog(QDialog):
    def __init__(self, editor, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self._editor = editor
        self.setWindowTitle("Find")
        self.setFixedHeight(34)  # VS Code default height
        self.setMinimumWidth(300)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self._replace_visible = False
        self._match_count = 0
        self._current_match_index = 0
        self._build_ui()
        self._position_widget()

    def _build_ui(self):
        # VS Code style - dark widget at top of editor
        self.setStyleSheet("""
            QDialog {
                background-color: #252526;
                border: 1px solid #454545;
                border-radius: 6px;
            }
        """)

        # Main vertical layout to support find + replace rows
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Find row
        find_row = QHBoxLayout()
        find_row.setContentsMargins(9, 4, 4, 4)
        find_row.setSpacing(3)

        # Find input
        self._find_edit = QLineEdit()
        self._find_edit.setPlaceholderText("Find")
        self._find_edit.setFixedHeight(25)
        self._find_edit.setMinimumWidth(150)
        self._find_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3C3C3C;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
                color: #CCCCCC;
                padding: 2px 6px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #3C3C3C;
            }
        """)
        self._find_edit.returnPressed.connect(self._find_next)
        find_row.addWidget(self._find_edit)

        # Navigation buttons
        self._btn_prev = QToolButton()
        self._btn_prev.setText("▲")
        self._btn_prev.setFixedSize(22, 22)
        self._btn_prev.setStyleSheet(self._button_style())
        self._btn_prev.setToolTip("Previous Match (Shift+Enter)")
        self._btn_prev.clicked.connect(self._find_prev)
        find_row.addWidget(self._btn_prev)

        self._btn_next = QToolButton()
        self._btn_next.setText("▼")
        self._btn_next.setFixedSize(22, 22)
        self._btn_next.setStyleSheet(self._button_style())
        self._btn_next.setToolTip("Next Match (Enter)")
        self._btn_next.clicked.connect(self._find_next)
        find_row.addWidget(self._btn_next)

        # Match count
        self._match_count_label = QLabel("No results")
        self._match_count_label.setStyleSheet("color: #858585; font-size: 12px; padding: 0 4px;")
        find_row.addWidget(self._match_count_label)

        # Option buttons
        self._btn_case = QToolButton()
        self._btn_case.setText("Aa")
        self._btn_case.setCheckable(True)
        self._btn_case.setFixedSize(22, 22)
        self._btn_case.setStyleSheet(self._toggle_button_style())
        self._btn_case.setToolTip("Match Case (Alt+C)")
        find_row.addWidget(self._btn_case)

        self._btn_word = QToolButton()
        self._btn_word.setText("Ab")
        self._btn_word.setCheckable(True)
        self._btn_word.setFixedSize(22, 22)
        self._btn_word.setStyleSheet(self._toggle_button_style())
        self._btn_word.setToolTip("Match Whole Word (Alt+W)")
        find_row.addWidget(self._btn_word)

        self._btn_regex = QToolButton()
        self._btn_regex.setText(".*")
        self._btn_regex.setCheckable(True)
        self._btn_regex.setFixedSize(22, 22)
        self._btn_regex.setStyleSheet(self._toggle_button_style())
        self._btn_regex.setToolTip("Use Regular Expression (Alt+R)")
        find_row.addWidget(self._btn_regex)

        # Replace toggle button
        self._btn_toggle_replace = QToolButton()
        self._btn_toggle_replace.setText("⇄")
        self._btn_toggle_replace.setCheckable(True)
        self._btn_toggle_replace.setFixedSize(22, 22)
        self._btn_toggle_replace.setStyleSheet(self._toggle_button_style())
        self._btn_toggle_replace.setToolTip("Toggle Replace")
        self._btn_toggle_replace.toggled.connect(self._toggle_replace)
        find_row.addWidget(self._btn_toggle_replace)

        # Close button
        close_btn = QToolButton()
        close_btn.setText("×")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet(self._button_style())
        close_btn.setToolTip("Close (Escape)")
        close_btn.clicked.connect(self.close)
        find_row.addWidget(close_btn)

        main_layout.addLayout(find_row)

        # Replace section (initially hidden)
        self._replace_widget = QWidget()
        replace_layout = QHBoxLayout(self._replace_widget)
        replace_layout.setContentsMargins(9, 0, 4, 4)
        replace_layout.setSpacing(3)

        self._replace_edit = QLineEdit()
        self._replace_edit.setPlaceholderText("Replace")
        self._replace_edit.setFixedHeight(25)
        self._replace_edit.setMinimumWidth(150)
        self._replace_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3C3C3C;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
                color: #CCCCCC;
                padding: 2px 6px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #3C3C3C;
            }
        """)
        replace_layout.addWidget(self._replace_edit)

        self._btn_replace = QToolButton()
        self._btn_replace.setText("Replace")
        self._btn_replace.setFixedSize(70, 22)
        self._btn_replace.setStyleSheet(self._button_style())
        self._btn_replace.setToolTip("Replace (Enter)")
        self._btn_replace.clicked.connect(self._replace_once)
        replace_layout.addWidget(self._btn_replace)

        self._btn_replace_all = QToolButton()
        self._btn_replace_all.setText("Replace All")
        self._btn_replace_all.setFixedSize(70, 22)
        self._btn_replace_all.setStyleSheet(self._button_style())
        self._btn_replace_all.setToolTip("Replace All")
        self._btn_replace_all.clicked.connect(self._replace_all)
        replace_layout.addWidget(self._btn_replace_all)

        self._replace_widget.hide()
        main_layout.addWidget(self._replace_widget)

        # Connections
        self._find_edit.textChanged.connect(self._on_find_text_changed)
        self._btn_case.toggled.connect(self._on_find_text_changed)
        self._btn_word.toggled.connect(self._on_find_text_changed)
        self._btn_regex.toggled.connect(self._on_find_text_changed)

    def _button_style(self):
        return """
            QToolButton {
                background: transparent;
                border: none;
                color: #858585;
                border-radius: 3px;
                font-size: 14px;
            }
            QToolButton:hover {
                background-color: #3C3C3C;
                color: #FFFFFF;
            }
        """

    def _toggle_button_style(self):
        return """
            QToolButton {
                background: transparent;
                border: none;
                color: #858585;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #3C3C3C;
                color: #FFFFFF;
            }
            QToolButton:checked {
                background-color: #3C3C3C;
                color: #FFFFFF;
            }
        """

    def _position_widget(self):
        """Position widget at top-right of editor like VS Code"""
        if self.parent():
            parent_geom = self.parent().geometry()
            # Position at top right with some margin
            x = parent_geom.x() + parent_geom.width() - 450
            y = parent_geom.y() + 10
            self.move(x, y)

    def _toggle_replace(self, checked):
        """Toggle replace section visibility"""
        if checked:
            self._replace_widget.show()
            self.setFixedHeight(62)  # Find row + replace row
        else:
            self._replace_widget.hide()
            self.setFixedHeight(34)  # Just find row

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _build_flags(self) -> re.RegexFlag:
        flags = re.MULTILINE
        if not self._btn_case.isChecked():
            flags |= re.IGNORECASE
        return flags

    def _make_pattern(self, text: str) -> re.Pattern | None:
        if not text:
            return None
        try:
            if self._btn_regex.isChecked():
                pat = text
            else:
                pat = re.escape(text)
            if self._btn_word.isChecked():
                pat = r"\b" + pat + r"\b"
            return re.compile(pat, self._build_flags())
        except re.error as e:
            self._match_count_label.setText(f"Regex error")
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
        if m is None:
            m = pattern.search(text, 0)
        if m:
            self._set_selection(m.start(), m.end())
            self._update_match_count(pattern, text, m.start())
        else:
            self._match_count_label.setText("No results")

    def _find_prev(self):
        pattern = self._make_pattern(self._find_edit.text())
        if not pattern:
            return
        text = self._get_text()
        cur = self._editor.textCursor()
        pos = cur.selectionStart()
        matches = list(pattern.finditer(text, 0, pos))
        if not matches:
            matches = list(pattern.finditer(text))
        if matches:
            m = matches[-1]
            self._set_selection(m.start(), m.end())
            self._update_match_count(pattern, text, m.start())
        else:
            self._match_count_label.setText("No results")

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
            self._match_count_label.setText(f"Replaced {count}")
        else:
            self._match_count_label.setText("No results")

    def _update_match_count(self, pattern, text, current_pos):
        """Update match count display in VS Code style (e.g., '1 of 5')"""
        matches = list(pattern.finditer(text))
        total = len(matches)
        if total == 0:
            self._match_count_label.setText("No results")
        else:
            # Find current match index
            current_index = 0
            for i, m in enumerate(matches):
                if m.start() == current_pos:
                    current_index = i + 1
                    break
            self._match_count_label.setText(f"{current_index} of {total}")

    def _on_find_text_changed(self):
        """Handle text change to update match count"""
        pattern = self._make_pattern(self._find_edit.text())
        if pattern:
            text = self._get_text()
            matches = list(pattern.finditer(text))
            total = len(matches)
            if total == 0:
                self._match_count_label.setText("No results")
            else:
                self._match_count_label.setText(f"{total} results")
        else:
            self._match_count_label.setText("No results")

    # ── Public API ───────────────────────────────────────────────────────────

    def set_search_term(self, text: str):
        self._find_edit.setText(text)
        self._find_edit.selectAll()

    def show_and_focus(self):
        self._position_widget()
        self.show()
        self.raise_()
        self.activateWindow()
        self._find_edit.setFocus()
        self._find_edit.selectAll()
        # Reset replace section to hidden when opening
        self._btn_toggle_replace.setChecked(False)
        self._replace_widget.hide()
        self.setFixedHeight(34)

    def keyPressEvent(self, event):
        # Handle Escape key to close
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        # Handle Enter in replace field
        if event.key() == Qt.Key.Key_Return and self._replace_edit.hasFocus():
            self._replace_once()
            return
        super().keyPressEvent(event)
