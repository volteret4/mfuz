"""
Stats Callbacks Module - Handles callbacks between StatsModule and its submodules
"""
import logging
from typing import Dict, Callable, Any

class StatsCallbackHandler:
    """
    A class to manage callbacks between the main StatsModule and its submodules.
    This acts as a central hub for all UI interactions in the stats module.
    """
    
    def __init__(self, stats_module=None):
        """
        Initialize the callback handler with a reference to the main StatsModule.
        
        Args:
            stats_module: Reference to the main StatsModule instance
        """
        self.stats_module = stats_module
        self.submodules = {}  # Dictionary to store references to submodules
        self.callbacks = {}   # Dictionary to store callback functions
        
    def register_submodule(self, name: str, submodule: Any) -> None:
        """
        Register a submodule with the callback handler.
        
        Args:
            name: A unique name for the submodule
            submodule: The submodule instance
        """
        if name in self.submodules:
            logging.warning(f"Overwriting existing submodule registration for '{name}'")
        
        self.submodules[name] = submodule
        logging.info(f"Registered submodule: {name}")
    
    def register_callback(self, event_name: str, callback: Callable, module_name: str = None) -> None:
        """
        Register a callback function for a specific event.
        
        Args:
            event_name: The name of the event to register for
            callback: The function to call when the event occurs
            module_name: Optional name of the module the callback belongs to
        """
        if event_name not in self.callbacks:
            self.callbacks[event_name] = []
        
        # Store the callback with its module info
        callback_info = {
            'function': callback,
            'module': module_name
        }
        
        self.callbacks[event_name].append(callback_info)
        logging.debug(f"Registered callback for event '{event_name}' from module '{module_name}'")
    
    def trigger_event(self, event_name: str, *args, **kwargs) -> None:
        """
        Trigger all callbacks registered for a specific event.
        
        Args:
            event_name: The name of the event to trigger
            *args, **kwargs: Arguments to pass to the callback functions
        """
        if event_name not in self.callbacks:
            logging.debug(f"No callbacks registered for event '{event_name}'")
            return
        
        # Call all registered callbacks for this event
        for callback_info in self.callbacks[event_name]:
            try:
                callback_function = callback_info['function']
                module_name = callback_info['module']
                
                logging.debug(f"Triggering callback for event '{event_name}' from module '{module_name}'")
                callback_function(*args, **kwargs)
                
            except Exception as e:
                logging.error(f"Error in callback for event '{event_name}': {e}")
                import traceback
                logging.error(traceback.format_exc())
    
    def setup_ui_connections(self) -> None:
        """Set up connections between UI elements and their handlers."""
        if not self.stats_module:
            logging.error("Cannot set up UI connections: stats_module is None")
            return
        
        # Connect the main category combo box
        category_combo = getattr(self.stats_module, 'category_combo', None)
        if category_combo:
            # Disconnect existing connections to avoid duplicates
            try:
                category_combo.currentIndexChanged.disconnect()
            except Exception:
                pass
            
            # Connect to our event-triggering function
            category_combo.currentIndexChanged.connect(
                lambda index: self.trigger_event('category_changed', index)
            )
            
            # Also register the main module's category change handler
            if hasattr(self.stats_module, 'change_category'):
                self.register_callback(
                    'category_changed',
                    self.stats_module.change_category,
                    'stats_module'
                )
        
        # Set up connections for the feeds submodule
        feeds_submodule = self.submodules.get('feeds', None)
        if feeds_submodule:
            # Let the submodule handle its own connections
            if hasattr(feeds_submodule, 'setup_connections'):
                feeds_submodule.setup_connections()
    
    def on_feeds_page_activated(self) -> None:
        """
        Handler for when the feeds page is activated.
        This should initialize or refresh the feeds data.
        """
        feeds_submodule = self.submodules.get('feeds', None)
        if feeds_submodule:
            # Load initial feeds statistics
            if hasattr(feeds_submodule, 'load_feed_stats'):
                feeds_submodule.load_feed_stats()
            else:
                logging.warning("Feeds submodule doesn't have load_feed_stats method")
    
    def redirect_to_submodule(self, method_name: str, submodule_name: str, *args, **kwargs) -> Any:
        """
        Redirect a method call to a specific submodule.
        
        Args:
            method_name: The name of the method to call on the submodule
            submodule_name: The name of the submodule to call the method on
            *args, **kwargs: Arguments to pass to the method
            
        Returns:
            The result of the method call, or None if the method doesn't exist
        """
        submodule = self.submodules.get(submodule_name, None)
        if not submodule:
            logging.warning(f"Submodule '{submodule_name}' not found")
            return None
        
        method = getattr(submodule, method_name, None)
        if not method or not callable(method):
            logging.warning(f"Method '{method_name}' not found in submodule '{submodule_name}'")
            return None
        
        # Call the method on the submodule
        try:
            return method(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error calling '{method_name}' on submodule '{submodule_name}': {e}")
            import traceback
            logging.error(traceback.format_exc())
            return None