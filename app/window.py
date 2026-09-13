"""
Main window for Notepad Minus.
Frameless window with custom dark title bar, full menu/toolbar,
status bar, file I/O, encoding, line-ending, Go-To-Line, etc.
"""

import os
import sys
from pathlib import Path

from PyQt6.QtCore import (
    QPoint, QRect, QSize, Qt, QTimer, pyqtSignal,
)
from PyQt6.QtGui import (
    QAction, QColor, QIcon,
    QKeySequence, QPainter, QPalette, QTextCursor,
    QCloseEvent,
)
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout,
    QInputDialog, QLabel, QMainWindow, QMenu,
    QMessageBox, QPushButton, QSizePolicy,
    QSizeGrip, QStatusBar, QToolBar, QVBoxLayout,
    QWidget, QMenuBar, QFrame, QSpacerItem,
)

from .editor import CodeEditor
from .spellcheck import SpellCheckEngine
from .autosave import AutoSaveManager
from .find_replace import FindReplaceDialog
from .dialogs import DarkMessageBox, DarkInputDialog
from .settings import Settings
from .theme import DARK_THEME, TITLE_BAR_STYLE


# ══════════════════════════════════════════════════════════════════════════════
#  Custom Title Bar
# ══════════════════════════════════════════════════════════════════════════════

class _TitleBar(QWidget):
    """Drag-to-move title bar with min/max/close buttons."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(36)
        self.setStyleSheet(TITLE_BAR_STYLE)

        self._win = parent
        self._drag_pos: QPoint | None = None
        self._maximized = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)

        # App icon + title
        self._icon_label = QLabel("◧")
        self._icon_label.setStyleSheet(
            "color: #8888FF; margin-right: 6px; background: transparent;"
        )
        layout.addWidget(self._icon_label)

        self._title_label = QLabel("Notepad Minus — Untitled")
        self._title_label.setStyleSheet(
            "color: #CCCCDD; background: transparent;"
        )
        layout.addWidget(self._title_label)
        layout.addStretch(1)

        # ── Window control buttons ──────────────────────────────────────────
        # Shared style: fixed 46×36, symbol centred, rounded pill hover
        _btn_common = """
            QPushButton {{
                background: transparent;
                border: none;
                color: {fg};
                padding: 0;
                margin: 0;
                border-radius: 0;
            }}
            QPushButton:hover {{
                background-color: {hbg};
                color: {hfg};
            }}
            QPushButton:pressed {{
                background-color: {pbg};
                color: {hfg};
            }}
        """

        self._btn_min = QPushButton("\u2014")  # em dash — looks like a clean underline
        self._btn_min.setFixedSize(46, 36)
        self._btn_min.setToolTip("Minimize")
        self._btn_min.setStyleSheet(_btn_common.format(
            fg="#9090B0",
            hbg="#2E2E44", hfg="#FFFFFF", pbg="#232338",
        ))

        self._btn_max = QPushButton("\u25A1")  # □ white square
        self._btn_max.setFixedSize(46, 36)
        self._btn_max.setToolTip("Maximize")
        self._btn_max.setStyleSheet(_btn_common.format(
            fg="#9090B0",
            hbg="#2E2E44", hfg="#FFFFFF", pbg="#232338",
        ))

        self._btn_close = QPushButton("\u00D7")  # × multiplication sign
        self._btn_close.setFixedSize(46, 36)
        self._btn_close.setToolTip("Close")
        self._btn_close.setStyleSheet(_btn_common.format(
            fg="#9090B0",
            hbg="#C0392B", hfg="#FFFFFF", pbg="#962D22",
        ))

        for btn in (self._btn_min, self._btn_max, self._btn_close):
            btn.setCursor(Qt.CursorShape.ArrowCursor)
            layout.addWidget(btn)

        self._btn_min.clicked.connect(self._win.showMinimized)
        self._btn_max.clicked.connect(self._toggle_max)
        self._btn_close.clicked.connect(self._win.close)

    def set_title(self, text: str):
        self._title_label.setText(text)

    def _toggle_max(self):
        if self._win.isMaximized():
            self._win.showNormal()
            self._btn_max.setText("\u25A1")   # □ restore
        else:
            self._win.showMaximized()
            self._btn_max.setText("\u25A3")   # ▣ filled square = maximised

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_max()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._win.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton) and self._drag_pos is not None:
            if self._win.isMaximized():
                self._win.showNormal()
                self._btn_max.setText("\u25A1")
                self._drag_pos = QPoint(self._win.width() // 2, self.height() // 2)
            self._win.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


# ══════════════════════════════════════════════════════════════════════════════
#  Resize Handle
# ══════════════════════════════════════════════════════════════════════════════

class _ResizableFramelessWindow(QWidget):
    """Base class that adds 8-direction resize to a frameless window."""

    MARGIN = 5

    def __init__(self):
        super().__init__()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self._resizing = False
        self._resize_dir = None
        self._resize_start_pos = QPoint()
        self._resize_start_geom = QRect()
        self.setMouseTracking(True)

    def _edge_flags(self, pos: QPoint):
        r = self.rect()
        m = self.MARGIN
        left = pos.x() < m
        right = pos.x() > r.width() - m
        top = pos.y() < m
        bottom = pos.y() > r.height() - m
        return left, right, top, bottom

    def _cursor_for_edge(self, pos: QPoint):
        left, right, top, bottom = self._edge_flags(pos)
        if (top and left) or (bottom and right):
            return Qt.CursorShape.SizeFDiagCursor
        if (top and right) or (bottom and left):
            return Qt.CursorShape.SizeBDiagCursor
        if left or right:
            return Qt.CursorShape.SizeHorCursor
        if top or bottom:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            left, right, top, bottom = self._edge_flags(event.pos())
            if any((left, right, top, bottom)):
                self._resizing = True
                self._resize_dir = (left, right, top, bottom)
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            g = QRect(self._resize_start_geom)
            left, right, top, bottom = self._resize_dir
            if left:
                g.setLeft(g.left() + delta.x())
            if right:
                g.setRight(g.right() + delta.x())
            if top:
                g.setTop(g.top() + delta.y())
            if bottom:
                g.setBottom(g.bottom() + delta.y())
            min_w, min_h = 400, 300
            if g.width() >= min_w and g.height() >= min_h:
                self.setGeometry(g)
            event.accept()
        else:
            self.setCursor(self._cursor_for_edge(event.pos()))
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resizing = False
        self._resize_dir = None
        super().mouseReleaseEvent(event)


# ══════════════════════════════════════════════════════════════════════════════
#  Main Window
# ══════════════════════════════════════════════════════════════════════════════

class MainWindow(_ResizableFramelessWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Notepad Minus")
        self.setMinimumSize(500, 350)
        self.resize(960, 640)

        # State
        self._current_path: str | None = None
        self._modified = False
        self._encoding = "UTF-8"
        self._line_ending = "CRLF"
        self._find_dialog: FindReplaceDialog | None = None

        # Services
        self._settings = Settings()
        self._spell_engine = SpellCheckEngine(self)
        self._autosave = AutoSaveManager(self)

        # Build UI
        self._build_ui()
        self._build_menu()
        self._build_toolbar()
        self._build_status_bar()
        self._connect_signals()
        self._restore_settings()

        # Status update timer
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(400)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start()

        # Auto-focus editor with caret at end
        QTimer.singleShot(0, self._focus_editor_at_end)

    def _focus_editor_at_end(self):
        self._editor.focus_caret_at_end()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        self._title_bar = _TitleBar(self)
        root.addWidget(self._title_bar)

        # Menu bar
        self._menu_bar = QMenuBar(self)
        self._menu_bar.setStyleSheet(
            "QMenuBar { background: #16161A; border-bottom: 1px solid #2A2A35; }"
        )
        root.addWidget(self._menu_bar)

        # Toolbar placeholder (filled in _build_toolbar)
        self._toolbar = QToolBar("Main", self)
        self._toolbar.setMovable(False)
        self._toolbar.setIconSize(QSize(16, 16))
        self._toolbar.setVisible(False)
        root.addWidget(self._toolbar)

        # Editor
        self._editor = CodeEditor(self._spell_engine, self)
        root.addWidget(self._editor, 1)

        # Status bar
        self._status_bar = QStatusBar(self)
        self._status_bar.setSizeGripEnabled(False)
        root.addWidget(self._status_bar)

        # Autosave setup
        self._autosave.setup(
            get_content_fn=self._editor.toPlainText,
            get_path_fn=lambda: self._current_path,
        )

    def _build_menu(self):
        mb = self._menu_bar

        # ── File
        file_menu = mb.addMenu("&File")
        self._act_new       = self._action("&New",               "Ctrl+N",    self._new_file)
        self._act_open      = self._action("&Open…",             "Ctrl+O",    self._open_file)
        self._act_save      = self._action("&Save",              "Ctrl+S",    self._save_file)
        self._act_save_as   = self._action("Save &As…",          "Ctrl+Shift+S", self._save_file_as)
        self._act_autosave  = self._checkable_action("Auto &Save", self._toggle_autosave, checked=True)
        self._act_exit      = self._action("E&xit",              "Alt+F4",    self.close)

        self._recent_menu = QMenu("&Recent Files", self)
        file_menu.addActions([self._act_new, self._act_open])
        file_menu.addMenu(self._recent_menu)
        file_menu.addSeparator()
        file_menu.addActions([self._act_save, self._act_save_as])
        file_menu.addSeparator()
        file_menu.addAction(self._act_autosave)
        file_menu.addSeparator()
        file_menu.addSeparator()
        file_menu.addAction(self._act_exit)
        file_menu.aboutToShow.connect(self._refresh_recent_menu)

        # ── Edit
        edit_menu = mb.addMenu("&Edit")
        self._act_undo      = self._action("&Undo",   "Ctrl+Z",       self._editor.undo)
        self._act_redo      = self._action("&Redo",   "Ctrl+Y",       self._editor.redo)
        self._act_cut       = self._action("Cu&t",    "Ctrl+X",       self._editor.cut)
        self._act_copy      = self._action("&Copy",   "Ctrl+C",       self._editor.copy)
        self._act_paste     = self._action("&Paste",  "Ctrl+V",       self._editor.paste)
        self._act_delete    = self._action("&Delete", "Del",          self._delete_selection)
        self._act_selall    = self._action("Select &All", "Ctrl+A",   self._editor.selectAll)
        self._act_goto      = self._action("&Go to Line…", "Ctrl+G",  self._goto_line)
        self._act_find      = self._action("&Find / Replace…", "Ctrl+F", self._show_find)
        self._act_time      = self._action("Date/&Time",  "F5",       self._insert_datetime)

        edit_menu.addActions([self._act_undo, self._act_redo])
        edit_menu.addSeparator()
        edit_menu.addActions([self._act_cut, self._act_copy, self._act_paste, self._act_delete])
        edit_menu.addSeparator()
        edit_menu.addActions([self._act_selall, self._act_goto])
        edit_menu.addSeparator()
        edit_menu.addAction(self._act_find)
        edit_menu.addSeparator()
        edit_menu.addAction(self._act_time)

        # ── View
        view_menu = mb.addMenu("&View")
        self._act_wrap       = self._checkable_action("&Word Wrap", self._toggle_wrap)
        self._act_linenum    = self._checkable_action("&Line Numbers", self._toggle_line_numbers, checked=True)
        self._act_toolbar    = self._checkable_action("&Toolbar", self._toggle_toolbar, checked=False)
        self._act_statusbar  = self._checkable_action("&Status Bar", self._toggle_statusbar, checked=True)
        self._act_spell      = self._checkable_action("&Spell Check", self._toggle_spell, checked=True)

        view_menu.addActions([self._act_wrap, self._act_linenum])
        view_menu.addSeparator()
        view_menu.addActions([self._act_toolbar, self._act_statusbar])
        view_menu.addSeparator()
        view_menu.addAction(self._act_spell)

        # ── Format
        fmt_menu = mb.addMenu("F&ormat")

        # Encoding submenu
        enc_menu = QMenu("&Encoding", self)
        for enc in ("UTF-8", "UTF-16", "ANSI"):
            act = QAction(enc, self)
            act.setCheckable(True)
            act.setChecked(enc == self._encoding)
            act.triggered.connect(lambda checked, e=enc: self._set_encoding(e))
            enc_menu.addAction(act)
        self._enc_menu = enc_menu

        # Line ending submenu
        le_menu = QMenu("&Line Ending", self)
        for le in ("CRLF", "LF", "CR"):
            act = QAction(le, self)
            act.setCheckable(True)
            act.setChecked(le == self._line_ending)
            act.triggered.connect(lambda checked, l=le: self._set_line_ending(l))
            le_menu.addAction(act)
        self._le_menu = le_menu

        fmt_menu.addMenu(enc_menu)
        fmt_menu.addMenu(le_menu)

        # ── Help
        help_menu = mb.addMenu("&Help")
        self._act_about = self._action("&About Notepad Minus", None, self._show_about)
        help_menu.addAction(self._act_about)

    def _build_toolbar(self):
        tb = self._toolbar
        tb.setStyleSheet(
            "QToolBar { background: #16161A; border-bottom: 1px solid #2A2A35; "
            "padding: 2px 6px; spacing: 2px; }"
        )

        def add_toolbar_action(act, icon_text):
            # Temporarily store the original text to set as tooltip
            original_text = act.text().replace("&", "")
            act.setIconText(icon_text)
            tb.addAction(act)

        add_toolbar_action(self._act_new, "🗋")
        add_toolbar_action(self._act_open, "📂")
        add_toolbar_action(self._act_save, "💾")
        tb.addSeparator()
        add_toolbar_action(self._act_undo, "↩")
        add_toolbar_action(self._act_redo, "↪")
        tb.addSeparator()
        add_toolbar_action(self._act_cut, "✂")
        add_toolbar_action(self._act_copy, "⎘")
        add_toolbar_action(self._act_paste, "📋")
        tb.addSeparator()
        add_toolbar_action(self._act_find, "🔍")

    def _build_status_bar(self):
        sb = self._status_bar

        self._lbl_pos      = QLabel("Ln 1, Col 1")
        self._lbl_words    = QLabel("Words: 0")
        self._lbl_chars    = QLabel("Chars: 0")
        self._lbl_encoding = QLabel(self._encoding)
        self._lbl_le       = QLabel(self._line_ending)
        self._lbl_save     = QLabel("●  Saved")

        for lbl in (self._lbl_pos, self._lbl_words, self._lbl_chars,
                    self._lbl_encoding, self._lbl_le, self._lbl_save):
            lbl.setStyleSheet("color: #777788; padding: 0 10px;")

        self._lbl_save.setStyleSheet("color: #4CAF50; padding: 0 10px;")

        sep_style = "background: #2A2A35; max-width: 1px; min-width: 1px; min-height: 14px; max-height:14px; margin: 0 2px;"

        def sep():
            s = QFrame()
            s.setStyleSheet(sep_style)
            return s

        sb.addWidget(self._lbl_pos)
        sb.addWidget(sep())
        sb.addWidget(self._lbl_words)
        sb.addWidget(sep())
        sb.addWidget(self._lbl_chars)
        sb.addPermanentWidget(self._lbl_save)
        sb.addPermanentWidget(sep())
        sb.addPermanentWidget(self._lbl_le)
        sb.addPermanentWidget(sep())
        sb.addPermanentWidget(self._lbl_encoding)

    def _connect_signals(self):
        self._editor.document().modificationChanged.connect(self._on_modified_changed)
        self._editor.document().contentsChanged.connect(self._on_contents_changed)
        self._editor.zoom_changed.connect(self._on_zoom_changed)
        self._autosave.saved.connect(self._on_autosaved)
        self._autosave.save_failed.connect(self._on_save_failed)

    # ── Settings Restore ──────────────────────────────────────────────────────

    def _restore_settings(self):
        s = self._settings

        # Word wrap (default on, but remember user preference)
        wrap = s.get("word_wrap")
        if wrap is None:
            wrap = True
        self._act_wrap.setChecked(wrap)
        self._editor.set_word_wrap(wrap)

        # Spell check
        spell = s.get("spell_check")
        self._act_spell.setChecked(spell)
        self._editor.set_spell_check(spell)

        # Editor zoom (Ctrl + scroll)
        self._editor.set_zoom_point_size(s.get("editor_zoom_size"))

        # Line numbers
        linenum = s.get("show_line_numbers")
        self._act_linenum.setChecked(linenum)
        self._editor._line_area.setVisible(linenum)
        if linenum:
            self._editor._update_line_area_width(0)
        else:
            self._editor.setViewportMargins(0, 0, 0, 0)

        # Encoding / line ending
        self._encoding = s.get("encoding", "UTF-8")
        self._line_ending = s.get("line_ending", "CRLF")
        self._autosave.set_encoding(self._encoding)

        # Toolbar and statusbar visibility
        show_tb = s.get("show_toolbar")
        self._act_toolbar.setChecked(show_tb)
        self._toolbar.setVisible(show_tb)

        show_sb = s.get("show_statusbar")
        self._act_statusbar.setChecked(show_sb)
        self._status_bar.setVisible(show_sb)

        # Auto-save
        autosave = s.get("auto_save")
        self._act_autosave.setChecked(autosave)
        self._autosave.set_enabled(autosave)

        # Window geometry (restore position/size but not maximized state)
        geom = s.get("window_geometry")
        screen = QApplication.primaryScreen().geometry()
        if geom:
            try:
                # Check if saved geometry is suspiciously large (likely from maximized state)
                if geom[2] >= screen.width() - 50 or geom[3] >= screen.height() - 50:
                    # Reset to default size if it's too large
                    self.resize(960, 640)
                else:
                    self.setGeometry(*geom)
            except Exception:
                self.resize(960, 640)
        else:
            # Use default size if no geometry saved
            self.resize(960, 640)

    # ── Action Helpers ────────────────────────────────────────────────────────

    def _action(self, label: str, shortcut: str | None, slot) -> QAction:
        act = QAction(label, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(slot)
        self.addAction(act)
        return act

    def _checkable_action(self, label: str, slot, checked: bool = False) -> QAction:
        act = QAction(label, self)
        act.setCheckable(True)
        act.setChecked(checked)
        act.triggered.connect(slot)
        self.addAction(act)
        return act

    # ── File Operations ───────────────────────────────────────────────────────

    def _confirm_discard(self) -> bool:
        """Returns True if it's safe to discard current document."""
        if not self._modified:
            return True
        name = os.path.basename(self._current_path) if self._current_path else "Untitled"
        reply = DarkMessageBox.question(
            self, "Unsaved Changes",
            f'"{name}" has unsaved changes.\nSave before closing?'
        )
        if reply == 1:  # Save
            return self._save_file()
        return reply == 2  # Don't Save / Discard

    def _new_file(self):
        if not self._confirm_discard():
            return
        self._editor.clear()
        self._current_path = None
        self._modified = False
        self._editor.document().setModified(False)
        self._editor.focus_caret_at_end()
        self._update_title()

    def _open_file(self, path: str | None = None):
        if not self._confirm_discard():
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open File", "",
                "Text Files (*.txt);;All Files (*.*)",
            )
        if not path:
            return
        try:
            enc = self._encoding.lower().replace("-", "")
            enc_map = {"utf8": "utf-8", "utf16": "utf-16", "ansi": "cp1252"}
            enc = enc_map.get(enc, enc)
            with open(path, "r", encoding=enc, errors="replace") as f:
                content = f.read()
            self._editor.setPlainText(content)
            self._current_path = path
            self._modified = False
            self._editor.document().setModified(False)
            self._editor.open_file_view()
            self._update_title()
            self._settings.add_recent_file(path)
        except Exception as e:
            DarkMessageBox.critical(self, "Error", f"Cannot open file:\n{e}")

    def _save_file(self) -> bool:
        if self._current_path:
            return self._write_file(self._current_path)
        return self._save_file_as()

    def _save_file_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "",
            "Text Files (*.txt);;All Files (*.*)",
        )
        if not path:
            return False
        self._current_path = path
        self._settings.add_recent_file(path)
        return self._write_file(path)

    def _write_file(self, path: str) -> bool:
        try:
            enc = self._encoding.lower().replace("-", "")
            enc_map = {"utf8": "utf-8", "utf16": "utf-16", "ansi": "cp1252"}
            enc = enc_map.get(enc, enc)
            content = self._editor.toPlainText()
            # Apply line ending
            content = content.replace("\r\n", "\n").replace("\r", "\n")
            if self._line_ending == "CRLF":
                content = content.replace("\n", "\r\n")
            elif self._line_ending == "CR":
                content = content.replace("\n", "\r")
            with open(path, "w", encoding=enc, newline="") as f:
                f.write(content)
            self._modified = False
            self._editor.document().setModified(False)
            self._update_title()
            self._flash_saved()
            return True
        except Exception as e:
            DarkMessageBox.critical(self, "Save Error", f"Cannot save file:\n{e}")
            return False


    # ── Edit Operations ───────────────────────────────────────────────────────

    def _delete_selection(self):
        cur = self._editor.textCursor()
        if cur.hasSelection():
            cur.removeSelectedText()

    def _goto_line(self):
        total = self._editor.blockCount()
        line, ok = DarkInputDialog.getInt(
            self, "Go to Line", f"Line number (1 – {total}):",
            1, 1, total,
        )
        if ok:
            block = self._editor.document().findBlockByLineNumber(line - 1)
            cur = self._editor.textCursor()
            cur.setPosition(block.position())
            self._editor.setTextCursor(cur)
            self._editor.ensureCursorVisible()

    def _show_find(self):
        if self._find_dialog is None:
            self._find_dialog = FindReplaceDialog(self._editor, self)
        # Pre-fill with selected text
        cur = self._editor.textCursor()
        if cur.hasSelection():
            self._find_dialog.set_search_term(cur.selectedText())
        self._find_dialog.show_and_focus()

    def _insert_datetime(self):
        from datetime import datetime
        now = datetime.now().strftime("%I:%M %p  %m/%d/%Y")
        self._editor.textCursor().insertText(now)

    # ── View Operations ───────────────────────────────────────────────────────

    def _toggle_wrap(self):
        enabled = self._act_wrap.isChecked()
        self._editor.set_word_wrap(enabled)
        self._settings.set("word_wrap", enabled)

    def _toggle_line_numbers(self):
        enabled = self._act_linenum.isChecked()
        self._editor._line_area.setVisible(enabled)
        if enabled:
            self._editor._update_line_area_width(0)
        else:
            self._editor.setViewportMargins(0, 0, 0, 0)
        self._settings.set("show_line_numbers", enabled)

    def _toggle_toolbar(self):
        enabled = self._act_toolbar.isChecked()
        self._toolbar.setVisible(enabled)
        self._settings.set("show_toolbar", enabled)

    def _toggle_statusbar(self):
        enabled = self._act_statusbar.isChecked()
        self._status_bar.setVisible(enabled)
        self._settings.set("show_statusbar", enabled)

    def _toggle_spell(self):
        enabled = self._act_spell.isChecked()
        self._editor.set_spell_check(enabled)
        self._settings.set("spell_check", enabled)

    def _toggle_autosave(self):
        enabled = self._act_autosave.isChecked()
        self._autosave.set_enabled(enabled)
        self._settings.set("auto_save", enabled)

    # ── Format Operations ─────────────────────────────────────────────────────

    def _set_encoding(self, enc: str):
        self._encoding = enc
        self._autosave.set_encoding(enc)
        self._lbl_encoding.setText(enc)
        self._settings.set("encoding", enc)
        # Update checkmarks
        for act in self._enc_menu.actions():
            act.setChecked(act.text() == enc)

    def _set_line_ending(self, le: str):
        self._line_ending = le
        self._lbl_le.setText(le)
        self._settings.set("line_ending", le)
        for act in self._le_menu.actions():
            act.setChecked(act.text() == le)

    # ── About ─────────────────────────────────────────────────────────────────

    def _show_about(self):
        DarkMessageBox.about(
            self, "About Notepad Minus",
            "<h3>Notepad Minus</h3>"
            "<p>A professional, dark-themed Notepad replacement.</p>"
            "<p>Built with Python + PyQt6.<br>"
            "Real-time spell check · Auto-save · Find &amp; Replace · "
            "Custom dark title bar.</p>"
        )

    # ── Recent Files ──────────────────────────────────────────────────────────

    def _refresh_recent_menu(self):
        self._recent_menu.clear()
        recent = self._settings.recent_files
        if not recent:
            act = QAction("(empty)", self)
            act.setEnabled(False)
            self._recent_menu.addAction(act)
        else:
            for p in recent:
                act = QAction(os.path.basename(p), self)
                act.setToolTip(p)
                act.triggered.connect(lambda checked=False, path=p: self._open_file(path))
                self._recent_menu.addAction(act)
            self._recent_menu.addSeparator()
            clr = QAction("Clear Recent Files", self)
            clr.triggered.connect(lambda: self._settings.set("recent_files", []))
            self._recent_menu.addAction(clr)

    # ── Signal Handlers ───────────────────────────────────────────────────────

    def _on_zoom_changed(self, point_size: int):
        self._settings.set("editor_zoom_size", point_size)

    def _on_modified_changed(self, modified: bool):
        self._modified = modified
        self._update_title()

    def _on_contents_changed(self):
        self._set_unsaved_indicator()
        self._autosave.trigger()

    def _on_autosaved(self, path: str):
        if self._current_path is not None and path == self._current_path:
            self._modified = False
            self._editor.document().setModified(False)
            self._update_title()
            self._flash_saved()

    def _on_save_failed(self, err: str):
        self._lbl_save.setText("● Save Error")
        self._lbl_save.setStyleSheet("color: #FF4444; padding: 0 10px;")

    def _set_unsaved_indicator(self):
        self._lbl_save.setText("●  Unsaved")
        self._lbl_save.setStyleSheet("color: #FFAA44; padding: 0 10px;")

    def _flash_saved(self):
        self._lbl_save.setText("●  Saved")
        self._lbl_save.setStyleSheet("color: #4CAF50; padding: 0 10px;")

    def _update_status(self):
        ln, col = self._editor.current_line_col()
        self._lbl_pos.setText(f"Ln {ln}, Col {col}")
        self._lbl_words.setText(f"Words: {self._editor.word_count():,}")
        self._lbl_chars.setText(f"Chars: {self._editor.char_count():,}")

    def _update_title(self):
        name = os.path.basename(self._current_path) if self._current_path else "Untitled"
        mod_marker = " •" if self._modified else ""
        full_title = f"Notepad Minus — {name}{mod_marker}"
        self._title_bar.set_title(full_title)
        self.setWindowTitle(full_title)

    # ── Window Events ─────────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent):
        if not self._confirm_discard():
            event.ignore()
            return
        # Save window geometry only if not maximized
        if not self.isMaximized():
            g = self.geometry()
            self._settings.set("window_geometry", [g.x(), g.y(), g.width(), g.height()])
        else:
            # Clear geometry if maximized so it uses default size on next launch
            self._settings.set("window_geometry", None)
        self._autosave.flush()
        event.accept()

    def changeEvent(self, event):
        super().changeEvent(event)
        # Update max button icon when window state changes externally
        if hasattr(self, "_title_bar"):
            if self.isMaximized():
                self._title_bar._btn_max.setText("❐")
            else:
                self._title_bar._btn_max.setText("□")

    def keyPressEvent(self, event):
        # Extra global shortcuts
        if event.key() == Qt.Key.Key_F11:
            if self.isMaximized():
                self.showNormal()
            else:
                self.showMaximized()
            return
        super().keyPressEvent(event)
