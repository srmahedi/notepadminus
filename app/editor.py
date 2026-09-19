"""
Core editor widget with:
- Line number gutter
- Current-line highlight
- Real-time spell check (red wavy underlines)
- Right-click spelling suggestions
- Tab / indent helpers
- Ctrl + mouse wheel zoom (size remembered in settings)
"""

import re
from PyQt6.QtCore import (
    QPoint, QRect, QSize, Qt, pyqtSignal, QTimer,
)
from PyQt6.QtGui import (
    QColor, QFontMetrics, QMouseEvent, QPainter, QPen,
    QTextCursor, QTextOption, QKeySequence, QTextCharFormat,
    QPalette,
)
from PyQt6.QtWidgets import (
    QMenu, QPlainTextEdit, QTextEdit, QWidget,
)

from .fonts import EDITOR_FONT_DEFAULT_SIZE, editor_font
from .spellcheck import SpellCheckEngine, SpellHighlighter, WORD_RE

MIN_ZOOM_PT = 6
MAX_ZOOM_PT = 72
ZOOM_STEP = 1


# ── Line-number gutter ────────────────────────────────────────────────────────

class _LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


# ── Main editor ───────────────────────────────────────────────────────────────

class CodeEditor(QPlainTextEdit):
    """
    A QPlainTextEdit with line numbers, current-line highlight,
    spell-check underlines, and right-click suggestions.
    """

    spell_check_toggle = pyqtSignal(bool)
    zoom_changed = pyqtSignal(int)

    def __init__(self, spell_engine: SpellCheckEngine, parent=None):
        super().__init__(parent)
        self._spell_engine = spell_engine
        self._spell_enabled = True
        self._default_pt = EDITOR_FONT_DEFAULT_SIZE
        self._zoom_pt = self._default_pt

        # Line number area
        self._line_area = _LineNumberArea(self)
        self._line_area.installEventFilter(self)

        self.viewport().installEventFilter(self)

        # Spell highlighter
        self._highlighter = SpellHighlighter(self.document(), spell_engine)

        # Debounce timer for rehighlight after edits
        self._rehighlight_timer = QTimer(self)
        self._rehighlight_timer.setSingleShot(True)
        self._rehighlight_timer.setInterval(350)
        self._rehighlight_timer.timeout.connect(self._highlighter.rehighlight)

        # Connections
        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self.document().contentsChanged.connect(self._on_contents_changed)

        self._update_line_area_width(0)
        self._highlight_current_line()
        self._apply_zoom()
        self._apply_selection_colors()

    def _apply_selection_colors(self) -> None:
        """Ensure text selection contrasts with the dark editor background."""
        pal = self.palette()
        pal.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Highlight, QColor("#3C3C3C"))
        pal.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        pal.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, QColor("#3C3C3C"))
        pal.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        self.setPalette(pal)

    # ── Zoom (Ctrl + scroll) ─────────────────────────────────────────────────

    def zoom_point_size(self) -> int:
        return self._zoom_pt

    def set_zoom_point_size(self, size: int | None) -> None:
        if size is None:
            size = self._default_pt
        clamped = max(MIN_ZOOM_PT, min(MAX_ZOOM_PT, int(size)))
        if clamped == self._zoom_pt:
            return
        self._zoom_pt = clamped
        self._apply_zoom()
        self.zoom_changed.emit(self._zoom_pt)

    def _apply_zoom(self) -> None:
        self.setFont(editor_font(self._zoom_pt))
        self._update_line_area_width(0)

    def zoom_in(self, steps: int = 1) -> None:
        self.set_zoom_point_size(self._zoom_pt + steps * ZOOM_STEP)

    def zoom_out(self, steps: int = 1) -> None:
        self.set_zoom_point_size(self._zoom_pt - steps * ZOOM_STEP)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    # ── Open file: scroll to top, caret at end ───────────────────────────────

    def open_file_view(self) -> None:
        """Caret at end of document; viewport scrolled to the beginning."""
        self.setFocus()
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

        def _scroll_to_top():
            self.verticalScrollBar().setValue(0)
            self._highlight_current_line()

        QTimer.singleShot(0, _scroll_to_top)

    def focus_caret_at_end(self) -> None:
        """Move caret to end and scroll viewport to show it."""
        self.setFocus()
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self._highlight_current_line()

    def mousePressEvent(self, event: QMouseEvent):
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        super().mouseMoveEvent(event)

    def eventFilter(self, watched, event):
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab:
            cur = self.textCursor()
            if cur.hasSelection():
                self._indent_selection(cur)
            else:
                cur.insertText("    ")
            return
        if event.key() == Qt.Key.Key_Backtab:
            cur = self.textCursor()
            self._unindent_selection(cur)
            return
        super().keyPressEvent(event)

    # ── Spell check ──────────────────────────────────────────────────────────

    def set_spell_check(self, enabled: bool):
        self._spell_enabled = enabled
        self._highlighter.setEnabled(enabled)

    def _on_contents_changed(self):
        self._rehighlight_timer.start()

    # ── Word under cursor helper ──────────────────────────────────────────────

    def _word_at_cursor(self, pos: QPoint) -> tuple[str, int, int] | None:
        """Return (word, start_pos, end_pos) for the word at viewport pos."""
        cursor = self.cursorForPosition(pos)
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText()
        if not word or not re.match(r"[a-zA-Z']+", word):
            return None
        return word, cursor.selectionStart(), cursor.selectionEnd()

    # ── Context menu (spell suggestions) ─────────────────────────────────────

    def contextMenuEvent(self, event):
        std_menu = self.createStandardContextMenu()

        if self._spell_enabled and self._spell_engine.available:
            info = self._word_at_cursor(event.pos())
            if info:
                word, start, end = info
                if not self._spell_engine.check(word):
                    suggestions = self._spell_engine.suggestions(word)

                    spell_menu = QMenu("Spelling", self)
                    spell_menu.setTitle(f'"{word}" — Suggestions')

                    if suggestions:
                        for sug in suggestions:
                            act = spell_menu.addAction(sug)
                            # capture sug + positions in closure
                            act.triggered.connect(
                                lambda checked=False, s=sug, st=start, en=end:
                                self._replace_word(st, en, s)
                            )
                    else:
                        no_act = spell_menu.addAction("No suggestions")
                        no_act.setEnabled(False)

                    spell_menu.addSeparator()
                    ig_act = spell_menu.addAction(f'Ignore "{word}"')
                    ig_act.triggered.connect(
                        lambda: self._ignore_word(word)
                    )
                    add_act = spell_menu.addAction(f'Add "{word}" to Dictionary')
                    add_act.triggered.connect(
                        lambda: self._add_word(word)
                    )

                    # Prepend spell menu to standard menu
                    first = std_menu.actions()[0] if std_menu.actions() else None
                    std_menu.insertMenu(first, spell_menu)
                    std_menu.insertSeparator(first)

        std_menu.exec(event.globalPos())

    def _replace_word(self, start: int, end: int, replacement: str):
        cur = self.textCursor()
        cur.setPosition(start)
        cur.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cur.insertText(replacement)

    def _ignore_word(self, word: str):
        self._spell_engine.ignore(word)
        self._highlighter.rehighlight()

    def _add_word(self, word: str):
        self._spell_engine.add_to_dictionary(word)
        self._highlighter.rehighlight()

    # ── Line number area ──────────────────────────────────────────────────────

    def line_number_area_width(self) -> int:
        digits = max(1, len(str(self.blockCount())))
        fm = QFontMetrics(self.font())
        space = 12 + fm.horizontalAdvance("9") * digits
        return space

    def _update_line_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_area(self, rect: QRect, dy: int):
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(),
                                   self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(
            QRect(cr.left(), cr.top(),
                  self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor("#252526"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + round(self.blockBoundingRect(block).height())

        current_line = self.textCursor().blockNumber()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                if block_number == current_line:
                    painter.setPen(QColor("#CCCCCC"))
                else:
                    painter.setPen(QColor("#858585"))
                painter.setFont(self.font())
                painter.drawText(
                    0, top,
                    self._line_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    # ── Current-line highlight ────────────────────────────────────────────────

    def _highlight_current_line(self):
        extra = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#2D2D30")
            selection.format.setBackground(line_color)
            selection.format.setProperty(
                QTextCharFormat.Property.FullWidthSelection, True
            )
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra.append(selection)
        self.setExtraSelections(extra)

    # ── Key handling ─────────────────────────────────────────────────────────

    def _indent_selection(self, cursor: QTextCursor):
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.beginEditBlock()
        while cursor.position() <= end:
            cursor.insertText("    ")
            end += 4
            if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
                break
        cursor.endEditBlock()

    def _unindent_selection(self, cursor: QTextCursor):
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.beginEditBlock()
        while cursor.position() <= end:
            line_cursor = self.textCursor()
            line_cursor.setPosition(cursor.position())
            line_cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            line_text = line_cursor.selectedText()
            spaces = len(line_text) - len(line_text.lstrip(" "))
            remove = min(spaces, 4)
            if remove:
                for _ in range(remove):
                    cursor.deleteChar()
                end -= remove
            if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
                break
        cursor.endEditBlock()

    # ── Word wrap ─────────────────────────────────────────────────────────────

    def set_word_wrap(self, enabled: bool):
        if enabled:
            self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        else:
            self.setWordWrapMode(QTextOption.WrapMode.NoWrap)

    # ── Stat helpers ──────────────────────────────────────────────────────────

    def word_count(self) -> int:
        return len(self.toPlainText().split())

    def char_count(self) -> int:
        return len(self.toPlainText())

    def current_line_col(self) -> tuple[int, int]:
        cur = self.textCursor()
        return cur.blockNumber() + 1, cur.columnNumber() + 1
