"""
Filter Manager - Manages message filters and triggers
Extracted from main_window.py to reduce complexity
"""
from typing import Dict, List, Callable, Optional, Any
from ..models.can_message import CANMessage


class FilterManager:
    """Manages message filtering and trigger logic"""
    
    def __init__(self, logger: Any):
        """
        Initialize filter manager
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        
        # Message filters
        self.filters_enabled = False
        self.id_filters: List[int] = []
        self.filter_mode = 'whitelist'  # 'whitelist' or 'blacklist'
        
        # Triggers
        self.triggers_enabled = False
        self.triggers: List[Dict] = []
        
        # Callbacks
        self.on_trigger_fired: Optional[Callable[[Dict, CANMessage], None]] = None
    
    def set_filters(self, filters: Dict):
        """
        Set message filters
        
        Args:
            filters: Dictionary with filter configuration
                {
                    'enabled': bool,
                    'id_filters': List[int],
                    'mode': 'whitelist' or 'blacklist'
                }
        """
        self.filters_enabled = filters.get('enabled', False)
        self.id_filters = filters.get('id_filters', [])
        self.filter_mode = filters.get('mode', 'whitelist')
        
        self.logger.info(f"Filters updated: enabled={self.filters_enabled}, "
                        f"mode={self.filter_mode}, count={len(self.id_filters)}")
    
    def get_filters(self) -> Dict:
        """Get current filter configuration"""
        return {
            'enabled': self.filters_enabled,
            'id_filters': self.id_filters,
            'mode': self.filter_mode
        }
    
    def set_triggers(self, triggers: Dict):
        """
        Set triggers
        
        Args:
            triggers: Dictionary with trigger configuration
                {
                    'enabled': bool,
                    'triggers': List[Dict]
                }
        """
        self.triggers_enabled = triggers.get('enabled', False)
        self.triggers = triggers.get('triggers', [])
        
        self.logger.info(f"Triggers updated: enabled={self.triggers_enabled}, "
                        f"count={len(self.triggers)}")
    
    def get_triggers(self) -> Dict:
        """Get current trigger configuration"""
        return {
            'enabled': self.triggers_enabled,
            'triggers': self.triggers
        }
    
    def message_passes_filter(self, msg: CANMessage) -> bool:
        """
        Check if message passes current filters
        
        Args:
            msg: CAN message to check
            
        Returns:
            True if message should be displayed
        """
        # If filters disabled, all messages pass
        if not self.filters_enabled:
            return True
        
        # If no filters configured, all messages pass
        if not self.id_filters:
            return True
        
        # Check filter mode
        if self.filter_mode == 'whitelist':
            # Whitelist: only show IDs in the list
            return msg.can_id in self.id_filters
        else:
            # Blacklist: hide IDs in the list
            return msg.can_id not in self.id_filters
    
    def check_triggers(self, msg: CANMessage):
        """
        Check if message matches any triggers
        
        Args:
            msg: CAN message to check
        """
        if not self.triggers_enabled:
            return
        
        for trigger in self.triggers:
            if self._trigger_matches(trigger, msg):
                self.logger.info(f"Trigger fired: {trigger.get('name', 'Unnamed')}")
                
                if self.on_trigger_fired:
                    self.on_trigger_fired(trigger, msg)
    
    def _trigger_matches(self, trigger: Dict, msg: CANMessage) -> bool:
        """
        Check if message matches trigger conditions
        
        Args:
            trigger: Trigger configuration
            msg: CAN message
            
        Returns:
            True if trigger conditions are met
        """
        # Check CAN ID
        trigger_id = trigger.get('can_id')
        if trigger_id is not None and msg.can_id != trigger_id:
            return False
        
        # Check data pattern
        data_pattern = trigger.get('data_pattern')
        if data_pattern:
            # Simple byte-by-byte comparison
            for i, expected_byte in enumerate(data_pattern):
                if expected_byte is not None:  # None means "don't care"
                    if i >= len(msg.data) or msg.data[i] != expected_byte:
                        return False
        
        # Check DLC
        trigger_dlc = trigger.get('dlc')
        if trigger_dlc is not None and msg.dlc != trigger_dlc:
            return False
        
        # Check source (channel)
        trigger_source = trigger.get('source')
        if trigger_source and msg.source != trigger_source:
            return False
        
        # All conditions met
        return True
    
    def add_id_filter(self, can_id: int):
        """Add a CAN ID to the filter list"""
        if can_id not in self.id_filters:
            self.id_filters.append(can_id)
            self.logger.debug(f"Added ID filter: 0x{can_id:X}")
    
    def remove_id_filter(self, can_id: int):
        """Remove a CAN ID from the filter list"""
        if can_id in self.id_filters:
            self.id_filters.remove(can_id)
            self.logger.debug(f"Removed ID filter: 0x{can_id:X}")
    
    def clear_filters(self):
        """Clear all filters"""
        self.id_filters.clear()
        self.filters_enabled = False
        self.logger.info("Filters cleared")
    
    def clear_triggers(self):
        """Clear all triggers"""
        self.triggers.clear()
        self.triggers_enabled = False
        self.logger.info("Triggers cleared")
