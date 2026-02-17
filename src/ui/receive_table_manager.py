"""
Receive Table Manager

Manages receive table configuration and message display.
Extracted from main_window.py to reduce complexity.
"""

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt
from typing import Optional, Dict
from ..models.can_message import CANMessage


class ReceiveTableManager:
    """Manages receive table configuration and message display"""
    
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
        
        # Restore context menu policy (don't lose the signal connections)
        table.setContextMenuPolicy(context_policy)
    
    def add_message_tracer(self, table: QTableWidget, msg: CANMessage, highlight: bool = True):
        """
        Add message in Tracer mode
        
        Args:
            table: Target table widget
            msg: CAN message to add
            highlight: Whether to highlight the message
        """
        # Prepare data via handler
        row = table.rowCount()
        row_data = self.message_handler.prepare_tracer_row_data(msg, row)
        
        table.insertRow(row)
        
        # Create items with alignment
        id_item = QTableWidgetItem(row_data['id'])
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        id_item.setData(Qt.ItemDataRole.UserRole, row_data['msg_index'])
        
        dlc_item = QTableWidgetItem(row_data['dlc'])
        dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        channel_item = QTableWidgetItem(row_data['channel'])
        channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set items
        table.setItem(row, 0, id_item)
        table.setItem(row, 1, QTableWidgetItem(row_data['time']))
        table.setItem(row, 2, channel_item)
        table.setItem(row, 3, QTableWidgetItem(row_data['pid']))
        table.setItem(row, 4, dlc_item)
        table.setItem(row, 5, QTableWidgetItem(row_data['data']))
        table.setItem(row, 6, QTableWidgetItem(row_data['ascii']))
        table.setItem(row, 7, QTableWidgetItem(row_data['comment']))
        
        # Auto-scroll
        table.scrollToBottom()
    
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
        if self.diff_manager and getattr(self.diff_manager, "config", None) and self.diff_manager.config.enabled:
            decision = self.diff_manager.evaluate(msg)
            if not decision.display:
                return
            mode = (getattr(self.diff_manager.config, "mode", "filter") or "filter").strip().lower()
            if mode in ("highlight", "both"):
                # cansniffer-like: highlight delta bytes vs snapshot baseline
                row_data['data'] = self.diff_manager.format_data_with_delta(
                    msg, decision.changed_indices_vs_snapshot
                )
        
        # Check if row already exists for this PID and Channel
        # Compare by PID and source channel (without gateway indicator)
        existing_row = -1
        for row in range(table.rowCount()):
            pid_item = table.item(row, 3)  # Column 3 = PID
            channel_item = table.item(row, 2)  # Column 2 = Channel
            if pid_item and channel_item:
                # Extract channel name without emoji indicators
                existing_channel = channel_item.text().split()[0] if channel_item.text() else ""
                new_channel = msg.source
                if pid_item.text() == row_data['pid'] and existing_channel == new_channel:
                    existing_row = row
                    break
        
        if existing_row >= 0:
            # Update existing row
            count_item = QTableWidgetItem(row_data['count'])
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(existing_row, 1, count_item)
            
            # Update channel (to show gateway indicator)
            channel_item = QTableWidgetItem(row_data['channel'])
            channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(existing_row, 2, channel_item)
            
            table.setItem(existing_row, 5, QTableWidgetItem(row_data['data']))
            table.setItem(existing_row, 6, QTableWidgetItem(row_data['period']))
            table.setItem(existing_row, 7, QTableWidgetItem(row_data['ascii']))
            
            # Highlight count cell if needed
            if highlight and row_data['should_highlight']:
                count_item.setBackground(colors['highlight'])
            else:
                count_item.setBackground(colors['normal_bg'])
                
            # Clear background of other cells
            for col in range(table.columnCount()):
                if col == 1:
                    continue
                item = table.item(existing_row, col)
                if item:
                    item.setBackground(colors['normal_bg'])
        else:
            # Add new row at the correct position (sorted by PID)
            # Find correct position to insert (sorted by PID, then Channel)
            insert_row = table.rowCount()
            
            for row in range(table.rowCount()):
                existing_pid_item = table.item(row, 3)
                existing_channel_item = table.item(row, 2)
                if existing_pid_item:
                    existing_pid_str = existing_pid_item.text()
                    try:
                        existing_pid = int(existing_pid_str.replace("0x", ""), 16)
                        if row_data['can_id'] < existing_pid:
                            insert_row = row
                            break
                        elif row_data['can_id'] == existing_pid and existing_channel_item:
                            if row_data['channel'] < existing_channel_item.text():
                                insert_row = row
                                break
                    except ValueError:
                        pass
            
            # Insert row
            table.insertRow(insert_row)
            
            # Create items with alignment
            id_item = QTableWidgetItem(str(insert_row + 1))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            count_item = QTableWidgetItem(row_data['count'])
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            channel_item = QTableWidgetItem(row_data['channel'])
            channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            dlc_item = QTableWidgetItem(row_data['dlc'])
            dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Set items
            table.setItem(insert_row, 0, id_item)
            table.setItem(insert_row, 1, count_item)
            table.setItem(insert_row, 2, channel_item)
            table.setItem(insert_row, 3, QTableWidgetItem(row_data['pid']))
            table.setItem(insert_row, 4, dlc_item)
            table.setItem(insert_row, 5, QTableWidgetItem(row_data['data']))
            table.setItem(insert_row, 6, QTableWidgetItem(row_data['period']))
            table.setItem(insert_row, 7, QTableWidgetItem(row_data['ascii']))
            table.setItem(insert_row, 8, QTableWidgetItem(row_data['comment']))
            
            # Update ID column for all rows below
            for row in range(insert_row + 1, table.rowCount()):
                id_item = table.item(row, 0)
                if id_item:
                    id_item.setText(str(row + 1))
            
            # Highlight if needed
            if highlight and row_data['should_highlight']:
                count_item.setBackground(colors['highlight'])

    def sync_monitor_table_to_last_seen(self, table: QTableWidget, last_seen: Dict, colors: Dict):
        """
        Refresh Monitor table to latest frames without re-counting.
        Useful when disabling Diff, since the UI might have been suppressed.
        """
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
    
    def clear_table(self, table: QTableWidget):
        """Clear table contents"""
        table.setRowCount(0)
    
    def repopulate_tracer(self, table: QTableWidget, messages: list):
        """
        Repopulate table with messages in Tracer mode
        
        Args:
            table: Target table widget
            messages: List of CANMessage objects
        """
        if not messages:
            return
        
        table.setRowCount(len(messages))
        
        for row_idx, msg in enumerate(messages):
            row_data = self.message_handler.prepare_tracer_row_data(msg, row_idx)
            
            # Create items with alignment
            id_item = QTableWidgetItem(row_data['id'])
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setData(Qt.ItemDataRole.UserRole, row_data['msg_index'])
            
            dlc_item = QTableWidgetItem(row_data['dlc'])
            dlc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            channel_item = QTableWidgetItem(row_data['channel'])
            channel_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Set items
            table.setItem(row_idx, 0, id_item)
            table.setItem(row_idx, 1, QTableWidgetItem(row_data['time']))
            table.setItem(row_idx, 2, channel_item)
            table.setItem(row_idx, 3, QTableWidgetItem(row_data['pid']))
            table.setItem(row_idx, 4, dlc_item)
            table.setItem(row_idx, 5, QTableWidgetItem(row_data['data']))
            table.setItem(row_idx, 6, QTableWidgetItem(row_data['ascii']))
            table.setItem(row_idx, 7, QTableWidgetItem(row_data['comment']))
