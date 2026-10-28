"""
Receive Table Manager

Manages receive table configuration and message display.
Extracted from main_window.py to reduce complexity.
"""

from PyQt6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QApplication,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument, QAbstractTextDocumentLayout, QFontMetrics
from typing import Optional, Dict
import bisect
import weakref
from ..models.can_message import CANMessage


class _DiffDataBoldDelegate(QStyledItemDelegate):
    """Paint Data column with per-byte bold based on a list of changed indices."""

    CHANGED_INDICES_ROLE = int(Qt.ItemDataRole.UserRole) + 1

    def paint(self, painter, option, index):
        changed = index.data(self.CHANGED_INDICES_ROLE) or []
        if not changed:
            super().paint(painter, option, index)
            return

        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        tokens = [t for t in str(text).split(" ") if t != ""]

        # Coerce to ints safely (Qt can sometimes give list[str] back).
        changed_set = set()
        for v in changed:
            try:
                changed_set.add(int(v))
            except Exception:
                continue

        # Respect selection background/foreground.
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if is_selected:
            painter.save()
            painter.fillRect(option.rect, option.palette.highlight())
            painter.restore()
            text_color = option.palette.highlightedText().color().name()
        else:
            text_color = option.palette.text().color().name()

        def esc(s: str) -> str:
            return (
                s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

        parts = []
        for i, tok in enumerate(tokens):
            safe = esc(tok)
            parts.append(f"<b>{safe}</b>" if i in changed_set else safe)

        html = f"<span style='color: {text_color};'>{'&nbsp;'.join(parts)}</span>"

        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setHtml(html)
        doc.setTextWidth(option.rect.width())

        painter.save()
        painter.translate(option.rect.topLeft())
        clip = option.rect.translated(-option.rect.topLeft())
        painter.setClipRect(clip)
        ctx = QAbstractTextDocumentLayout.PaintContext()
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        fm = QFontMetrics(option.font)
        return fm.size(0, str(text))


class _RowNumberDelegate(QStyledItemDelegate):
    """Paint the frame number without storing it in an item.

    The ID column is the running frame counter. Storing that text means
    renumbering every row below an insertion (O(n) per new ID) and, in Tracer
    mode, after every ring-buffer drop. Painting it on demand makes renumbering
    free, and the offset keeps the counter absolute when old rows are dropped.
    """

    def __init__(self, table, manager):
        super().__init__(table)
        self._table = table
        self._manager = manager

    def _label(self, row: int) -> str:
        offset = self._manager.row_label_offset(self._table)
        return str(row + 1 + offset)

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = self._label(index.row())
        opt.displayAlignment = Qt.AlignmentFlag.AlignCenter
        widget = opt.widget
        style = widget.style() if widget is not None else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)

    def displayText(self, value, locale):
        return str(value) if value else ""


class ReceiveTableManager:
    """Manages receive table configuration and message display"""
    
    #: Tracer rows kept in the table (0/None = unlimited). Display only:
    #: saving/exporting still reads the full message list.
    DEFAULT_MAX_TRACER_ROWS = 20000

    def __init__(self, parent_window, message_handler):
        """
        Initialize receive table manager
        
        Args:
            parent_window: Main window instance
            message_handler: MessageHandler instance for data formatting
        """
        self.parent = parent_window
        self.message_handler = message_handler
        self.diff_manager = None  # Will be set when diff mode is enabled
        self.max_tracer_rows = self.DEFAULT_MAX_TRACER_ROWS

        # Per-table row index: {(can_id, source): row} + sorted keys for
        # insertion, so adding a frame is O(1) instead of scanning the table.
        self._tables = weakref.WeakKeyDictionary()

        # Tracer ring buffer: how many frames were dropped from the top, so the
        # ID column can keep counting instead of restarting at 1.
        self._row_offsets = weakref.WeakKeyDictionary()

        # Tracer batching: rows are buffered and inserted once per UI tick.
        self._batching = False
        self._pending_tracer = {}
    
    def setup_table(self, table: QTableWidget, tracer_mode: bool):
        """
        Configure table based on mode
        
        Args:
            table: Table widget to configure
            tracer_mode: True for Tracer mode, False for Monitor mode
        """
        from ..i18n import t
        
        # Preserve context menu and connections
        context_policy = table.contextMenuPolicy()
        # Store signal connections by disconnecting and reconnecting
        # This is a workaround since PyQt doesn't provide a way to query connections
        
        if tracer_mode:
            # Tracer mode: ID, Time, Channel, PID, DLC, Data, ASCII, Comment
            table.setColumnCount(8)
            table.setHorizontalHeaderLabels(['ID', 'Time', t('col_channel'), 'PID', 'DLC', 'Data', 'ASCII', 'Comment'])
            
            # Tracer mode: allow editing (Comment only)
            table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
            
            # Allow manual resize of all columns
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            
            # Set appropriate initial widths
            header.resizeSection(0, 60)   # ID (sequential)
            header.resizeSection(1, 100)  # Time
            header.resizeSection(2, 70)   # Channel
            header.resizeSection(3, 110)  # PID (CAN ID) - 12 characters
            header.resizeSection(4, 60)   # DLC
            header.resizeSection(5, 250)  # Data
            header.resizeSection(6, 100)  # ASCII
            header.resizeSection(7, 150)  # Comment
            
            # Allow last column to expand when space is available
            header.setStretchLastSection(True)
        else:
            # Monitor mode: ID, Count, Channel, PID, DLC, Data, Period, ASCII, Comment
            table.setColumnCount(9)
            table.setHorizontalHeaderLabels(['ID', 'Count', t('col_channel'), 'PID', 'DLC', 'Data', 'Period', 'ASCII', 'Comment'])
            
            # Monitor mode: do not allow editing (data is updated automatically)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            
            # Allow manual resize of all columns
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            
            # Set appropriate initial widths
            header.resizeSection(0, 40)   # ID (sequential)
            header.resizeSection(1, 60)   # Count
            header.resizeSection(2, 70)   # Channel
            header.resizeSection(3, 110)  # PID (CAN ID) - 12 characters
            header.resizeSection(4, 50)   # DLC
            header.resizeSection(5, 250)  # Data
            header.resizeSection(6, 70)   # Period
            header.resizeSection(7, 100)  # ASCII
            header.resizeSection(8, 150)  # Comment
            
            # Allow last column to expand when space is available
            header.setStretchLastSection(True)

            # Diff highlighting: paint changed bytes as bold in the Data column.
            table.setItemDelegateForColumn(5, _DiffDataBoldDelegate(table))
        
        # Sequential ID is painted from the row index (see _RowNumberDelegate).
        # The Qt vertical header would show the same number again on the left.
        table.verticalHeader().setVisible(False)
        table.setItemDelegateForColumn(0, _RowNumberDelegate(table, self))

        # Table layout changed: drop any cached row index for it.
        self.reset_index(table)

        # Restore context menu policy (don't lose the signal connections)
        table.setContextMenuPolicy(context_policy)
    
    # ------------------------------------------------------------------
    # Row index (Monitor mode upsert without scanning the table)
    # ------------------------------------------------------------------

    def reset_index(self, table: QTableWidget):
        """Forget the cached row index for ``table``."""
        try:
            del self._tables[table]
        except KeyError:
            pass

    def row_label_offset(self, table: QTableWidget) -> int:
        """Frames dropped from the top of ``table`` (keeps the ID column absolute)."""
        return self._row_offsets.get(table, 0)

    def frame_count(self, table: QTableWidget) -> int:
        """Total frames currently represented by ``table`` (rows + dropped)."""
        return table.rowCount() + self.row_label_offset(table)

    def _table_state(self, table: QTableWidget) -> Dict:
        """Return (and lazily rebuild) the row index of ``table``."""
        state = self._tables.get(table)
        if state is None or (state['index'] and len(state['index']) != table.rowCount()):
            state = {'index': {}, 'keys': []}
            self._build_index(table, state)
            self._tables[table] = state
        return state

    def _build_index(self, table: QTableWidget, state: Dict):
        """Rebuild the index by scanning the table once."""
        index = state['index']
        keys = state['keys']
        index.clear()
        keys.clear()
        for row in range(table.rowCount()):
            pid_item = table.item(row, 3)
            channel_item = table.item(row, 2)
            if not pid_item or not channel_item:
                continue
            try:
                can_id = int(pid_item.text().replace("0x", ""), 16)
            except ValueError:
                continue
            channel = channel_item.text().split()[0] if channel_item.text() else ""
            if (can_id, channel) in index:
                continue
            index[(can_id, channel)] = row
            keys.append((can_id, channel))

    # ------------------------------------------------------------------
    # Tracer mode (batched + bounded)
    # ------------------------------------------------------------------

    def begin_batch(self):
        """Start buffering Tracer rows (one insert per UI tick)."""
        self._batching = True
        self._pending_tracer = {}

    def end_batch(self):
        """Flush all buffered Tracer rows."""
        self._batching = False
        pending, self._pending_tracer = self._pending_tracer, {}
        for table, messages in pending.items():
            if messages:
                self._render_tracer(table, messages)

    def add_message_tracer(self, table: QTableWidget, msg: CANMessage,
                           highlight: bool = True, msg_index: Optional[int] = None):
        """
        Add message in Tracer mode

        When a batch is open the message is buffered and inserted with the rest
        of the tick, which keeps Qt from doing one insertRow per frame.

        Args:
            table: Target table widget
            msg: CAN message to add
            highlight: Whether to highlight the message
            msg_index: Index in the recorded list (for playback), if recording
        """
        if self._batching:
            self._pending_tracer.setdefault(table, []).append((msg, msg_index))
            return
        self._render_tracer(table, [(msg, msg_index)])

    def add_batch_tracer(self, table: QTableWidget, messages, highlight: bool = True):
        """Insert several Tracer rows at once (used on reload/filter changes)."""
        self._render_tracer(table, [(msg, None) for msg in messages])

    def _render_tracer(self, table: QTableWidget, entries):
        """Insert a batch of Tracer rows and enforce the row cap."""
        if not entries:
            return

        start = table.rowCount()
        if start == 0:
            # Table was emptied (reset/mode switch): the frame counter restarts.
            self._row_offsets[table] = 0
        # QTableWidget has no insertRows: growing rowCount appends empty rows
        # in one operation (Tracer always appends).
        table.setRowCount(start + len(entries))

        for offset, (msg, msg_index) in enumerate(entries):
            row = start + offset
            row_data = self.message_handler.prepare_tracer_row_data(msg, row)

            id_item = QTableWidgetItem("")  # painted by _RowNumberDelegate
            id_item.setData(
                Qt.ItemDataRole.UserRole,
                msg_index if msg_index is not None else row_data['msg_index'],
            )

            dlc_item = QTableWidgetItem(row_data['dlc'])
            dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            channel_item = QTableWidgetItem(row_data['channel'])
            channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            table.setItem(row, 0, id_item)
            table.setItem(row, 1, QTableWidgetItem(row_data['time']))
            table.setItem(row, 2, channel_item)
            table.setItem(row, 3, QTableWidgetItem(row_data['pid']))
            table.setItem(row, 4, dlc_item)
            table.setItem(row, 5, QTableWidgetItem(row_data['data']))
            table.setItem(row, 6, QTableWidgetItem(row_data['ascii']))
            table.setItem(row, 7, QTableWidgetItem(row_data['comment']))

        self._enforce_row_cap(table)

    def _enforce_row_cap(self, table: QTableWidget):
        """Drop the oldest Tracer rows once the cap is exceeded."""
        limit = self.max_tracer_rows
        if not limit or limit <= 0:
            return
        overflow = table.rowCount() - int(limit)
        if overflow > 0:
            # No QTableWidget::removeRows, but the underlying model has it and
            # it removes a block in one call.
            table.model().removeRows(0, overflow)
            # Keep the ID column counting from where it left off.
            self._row_offsets[table] = self.row_label_offset(table) + overflow

    def add_message_monitor(self, table: QTableWidget, msg: CANMessage, colors: Dict, highlight: bool = True):
        """
        Add message in Monitor mode (groups by ID)
        
        Args:
            table: Target table widget
            msg: CAN message to add
            colors: Color dictionary for highlighting
            highlight: Whether to highlight the message
        """
        # Keep counters/period updated regardless of Diff filtering.
        counter_key = (msg.can_id, msg.source)
        
        # Calculate period BEFORE updating timestamp
        period_str = self.message_handler.calculate_period(msg, counter_key)
        
        # Now update counter and timestamp
        counter_key = self.message_handler.update_counter(msg)
        
        # Prepare row data with pre-calculated period
        row_data = self.message_handler.prepare_monitor_row_data(msg, counter_key, period_str)

        # Diff mode: decide if we display this message (but do not affect counting).
        changed_indices = []
        if self.diff_manager and getattr(self.diff_manager, "config", None) and self.diff_manager.config.enabled:
            decision = self.diff_manager.evaluate(msg)
            if not decision.display:
                return
            mode = (getattr(self.diff_manager.config, "mode", "filter") or "filter").strip().lower()
            if mode in ("highlight", "both"):
                # Keep plain text; store indices for the delegate to render in bold.
                changed_indices = list(decision.changed_indices_vs_snapshot or [])
                row_data['data'] = self.diff_manager.format_data_with_delta(msg, changed_indices)

        # Look up the row through the index instead of scanning the table.
        state = self._table_state(table)
        key = (msg.can_id, msg.source)
        existing_row = state['index'].get(key)

        if existing_row is not None:
            self._update_monitor_row(table, existing_row, row_data, changed_indices, colors, highlight)
            return

        # New ID: insert at its sorted position and shift the indexed rows.
        keys = state['keys']
        insert_row = bisect.bisect_left(keys, key)
        table.insertRow(insert_row)
        keys.insert(insert_row, key)

        index = state['index']
        for k, r in index.items():
            if r >= insert_row:
                index[k] = r + 1
        index[key] = insert_row

        count_item = QTableWidgetItem(row_data['count'])
        count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        channel_item = QTableWidgetItem(row_data['channel'])
        channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        dlc_item = QTableWidgetItem(row_data['dlc'])
        dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # Column 0 is painted by _RowNumberDelegate, no item needed.
        table.setItem(insert_row, 1, count_item)
        table.setItem(insert_row, 2, channel_item)
        table.setItem(insert_row, 3, QTableWidgetItem(row_data['pid']))
        table.setItem(insert_row, 4, dlc_item)
        data_item = QTableWidgetItem(row_data['data'])
        data_item.setData(_DiffDataBoldDelegate.CHANGED_INDICES_ROLE, changed_indices)
        table.setItem(insert_row, 5, data_item)
        table.setItem(insert_row, 6, QTableWidgetItem(row_data['period']))
        table.setItem(insert_row, 7, QTableWidgetItem(row_data['ascii']))
        table.setItem(insert_row, 8, QTableWidgetItem(row_data['comment']))

        # Highlight if needed
        if highlight and row_data['should_highlight']:
            count_item.setBackground(colors['highlight'])

    def _update_monitor_row(self, table: QTableWidget, row: int, row_data: Dict,
                            changed_indices, colors: Dict, highlight: bool):
        """Refresh an existing Monitor row (same CAN ID + source)."""
        count_item = QTableWidgetItem(row_data['count'])
        count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(row, 1, count_item)

        channel_item = QTableWidgetItem(row_data['channel'])
        channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(row, 2, channel_item)

        data_item = QTableWidgetItem(row_data['data'])
        data_item.setData(_DiffDataBoldDelegate.CHANGED_INDICES_ROLE, changed_indices)
        table.setItem(row, 5, data_item)
        table.setItem(row, 6, QTableWidgetItem(row_data['period']))
        table.setItem(row, 7, QTableWidgetItem(row_data['ascii']))

        if highlight and row_data['should_highlight']:
            count_item.setBackground(colors['highlight'])
        else:
            count_item.setBackground(colors['normal_bg'])

        # Clear background of other cells
        for col in range(table.columnCount()):
            if col == 1:
                continue
            item = table.item(row, col)
            if item:
                item.setBackground(colors['normal_bg'])

    def sync_monitor_table_to_last_seen(self, table: QTableWidget, last_seen: Dict, colors: Dict):
        """
        Refresh Monitor table to latest frames without re-counting.
        Useful when disabling Diff, since the UI might have been suppressed.
        """
        # This path scans/inserts directly; rebuild the index afterwards.
        self.reset_index(table)
        for msg in last_seen.values():
            counter_key = (msg.can_id, msg.source)
            # Period can't be reconstructed reliably here (last timestamp == msg.timestamp), keep blank.
            row_data = self.message_handler.prepare_monitor_row_data(msg, counter_key, period_str="")
            # Ensure raw (non-diff) data rendering
            row_data['data'] = " ".join([f"{b:02X}" for b in msg.data])

            # Reuse the existing upsert logic by calling add_message_monitor "manually":
            # we can't call add_message_monitor() because it would increment counters again.
            # So we replicate the minimal update path below.
            existing_row = -1
            for row in range(table.rowCount()):
                pid_item = table.item(row, 3)
                channel_item = table.item(row, 2)
                if pid_item and channel_item:
                    existing_channel = channel_item.text().split()[0] if channel_item.text() else ""
                    if pid_item.text() == row_data['pid'] and existing_channel == msg.source:
                        existing_row = row
                        break

            if existing_row >= 0:
                count_item = QTableWidgetItem(row_data['count'])
                count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(existing_row, 1, count_item)

                channel_item = QTableWidgetItem(row_data['channel'])
                channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(existing_row, 2, channel_item)

                table.setItem(existing_row, 4, QTableWidgetItem(row_data['dlc']))
                table.setItem(existing_row, 5, QTableWidgetItem(row_data['data']))
                table.setItem(existing_row, 6, QTableWidgetItem(row_data['period']))
                table.setItem(existing_row, 7, QTableWidgetItem(row_data['ascii']))
                table.setItem(existing_row, 8, QTableWidgetItem(row_data['comment']))
            else:
                insert_row = table.rowCount()
                table.insertRow(insert_row)

                id_item = QTableWidgetItem(str(insert_row + 1))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                count_item = QTableWidgetItem(row_data['count'])
                count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                channel_item = QTableWidgetItem(row_data['channel'])
                channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                dlc_item = QTableWidgetItem(row_data['dlc'])
                dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                table.setItem(insert_row, 0, id_item)
                table.setItem(insert_row, 1, count_item)
                table.setItem(insert_row, 2, channel_item)
                table.setItem(insert_row, 3, QTableWidgetItem(row_data['pid']))
                table.setItem(insert_row, 4, dlc_item)
                table.setItem(insert_row, 5, QTableWidgetItem(row_data['data']))
                table.setItem(insert_row, 6, QTableWidgetItem(row_data['period']))
                table.setItem(insert_row, 7, QTableWidgetItem(row_data['ascii']))
                table.setItem(insert_row, 8, QTableWidgetItem(row_data['comment']))

        self.reset_index(table)

    def clear_table(self, table: QTableWidget):
        """Clear table contents"""
        table.setRowCount(0)
        self.reset_index(table)
        self._row_offsets[table] = 0

    def repopulate_tracer(self, table: QTableWidget, messages: list, start_index: int = 0):
        """
        Repopulate table with messages in Tracer mode
        
        Args:
            table: Target table widget
            messages: List of CANMessage objects
            start_index: Index of ``messages[0]`` in the recorded list (playback)
        """
        table.setRowCount(0)
        self._row_offsets[table] = 0
        self.reset_index(table)

        if not messages:
            return

        # Insert in chunks so a long log doesn't freeze the UI.
        chunk = 500
        for start in range(0, len(messages), chunk):
            self._render_tracer(
                table,
                [(msg, start_index + start + i) for i, msg in enumerate(messages[start:start + chunk])],
            )

