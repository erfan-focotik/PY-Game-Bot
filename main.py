"""
Game Bot - Main Application Entry Point.
General-Purpose PC Game Bot with custom scripting engine, computer vision, and UI overlay.
"""

import sys
import time
import threading
from typing import Optional

# Add src to path
sys.path.insert(0, 'src')

from src.capture import ScreenCapture, get_capture_engine
from src.vision import VisionPipeline, get_vision_pipeline
from src.scripting import create_script_engine, ScriptInterpreter, BotAPI
from src.ui import ConfigWindow, RuntimeOverlay
from src.utils import (
    get_process_manager, 
    load_script_file, 
    list_game_processes,
    setup_template_folders
)


class GameBot:
    """
    Main application class that orchestrates all components.
    """

    def __init__(self):
        self.capture_engine: Optional[ScreenCapture] = None
        self.vision_pipeline: Optional[VisionPipeline] = None
        self.script_interpreter: Optional[ScriptInterpreter] = None
        self.bot_api: Optional[BotAPI] = None
        self.config_window: Optional[ConfigWindow] = None
        self.runtime_overlay: Optional[RuntimeOverlay] = None
        self.process_manager = get_process_manager()
        
        self.state = 'STOPPED'  # STOPPED, RUNNING, PAUSED
        self.script_thread: Optional[threading.Thread] = None
        self.config_values = {}

    def initialize(self, template_folder: str = 'assets/templates'):
        """Initialize all bot components."""
        print("=== Initializing Game Bot ===")
        
        # Setup template folders
        setup_template_folders(template_folder)
        
        # Initialize capture engine
        self.capture_engine = get_capture_engine(fps_target=60)
        
        # Initialize vision pipeline
        self.vision_pipeline = get_vision_pipeline(
            template_folder=template_folder,
            yolo_model_path=None,  # Set path to YOLO model if available
            use_gpu=False
        )
        
        # Initialize scripting engine
        self.script_interpreter, self.bot_api = create_script_engine()
        
        print("Initialization complete.\n")

    def select_process(self, process_name: str = None, pid: int = None) -> bool:
        """Select target game process."""
        if process_name:
            return self.process_manager.select_process(name=process_name)
        elif pid:
            return self.process_manager.select_process(pid=pid)
        else:
            # Show process selection menu
            print("\n=== Select Target Process ===")
            processes = list_game_processes()[:20]  # Show first 20
            
            for i, proc in enumerate(processes, 1):
                print(f"{i}. {proc['name']} (PID: {proc['pid']})")
            
            try:
                choice = input("\nEnter process name or PID: ").strip()
                if choice.isdigit():
                    return self.process_manager.select_process(pid=int(choice))
                else:
                    return self.process_manager.select_process(name=choice)
            except KeyboardInterrupt:
                return False
        
        return False

    def load_script(self, script_path: str) -> bool:
        """Load a bot script file."""
        try:
            print(f"\nLoading script: {script_path}")
            script_content = load_script_file(script_path)
            self.script_interpreter.load_script(script_content)
            print("Script loaded successfully.")
            return True
        except Exception as e:
            print(f"Failed to load script: {e}")
            return False

    def configure(self) -> bool:
        """Show configuration window and collect user settings."""
        config_vars = self.script_interpreter.get_config_variables()
        
        if not config_vars:
            print("No configuration variables found in script.")
            return True
        
        print("\n=== Bot Configuration ===")
        
        # Convert dataclasses to dicts for UI
        config_dicts = []
        for var in config_vars:
            config_dicts.append({
                'name': var.name,
                'var_type': var.var_type,
                'default_value': var.default_value,
                'min_value': var.min_value,
                'max_value': var.max_value,
                'options': var.options
            })
        
        def on_confirm(values):
            self.config_values = values
            print(f"Configuration confirmed: {values}")
        
        # Show GUI or console config
        self.config_window = ConfigWindow(config_dicts, on_confirm)
        self.config_values = self.config_window.show()
        
        # Apply config values to bot API
        for name, value in self.config_values.items():
            self.bot_api.set_config_value(name, value)
        
        return True

    def start(self):
        """Start the bot execution."""
        if self.state == 'RUNNING':
            print("Bot is already running.")
            return
        
        print("\n=== Starting Bot ===")
        
        # Get window region for capture
        window_region = self.process_manager.get_window_region()
        if window_region:
            self.capture_engine.set_region(window_region)
        
        # Start capture engine
        self.capture_engine.start()
        
        # Start vision pipeline
        self.vision_pipeline.start(self.capture_engine.frame_queue)
        
        # Start runtime overlay
        self.runtime_overlay = RuntimeOverlay(
            on_pause=self.toggle_pause,
            on_restart=self.restart,
            on_quit=self.stop
        )
        self.runtime_overlay.start()
        
        # Start script execution thread
        self.state = 'RUNNING'
        self.script_thread = threading.Thread(target=self._script_loop, daemon=True)
        self.script_thread.start()
        
        print("Bot started. Use overlay controls or console commands.")
        print("Press Ctrl+C to stop.\n")

    def _script_loop(self):
        """Main script execution loop."""
        while self.state == 'RUNNING':
            # Get latest vision results
            vision_results = self.vision_pipeline.get_results(timeout=0.1)
            
            if vision_results:
                # Update bot API with vision data
                self.bot_api.set_vision_results(vision_results)
                
                # Execute one iteration of the script
                try:
                    self.script_interpreter.execute()
                except Exception as e:
                    print(f"Script error: {e}")
                    break
            
            # Small delay to prevent CPU spinning
            time.sleep(0.01)

    def toggle_pause(self):
        """Toggle pause state."""
        if self.state == 'RUNNING':
            self.state = 'PAUSED'
            self.bot_api._paused = True
            if self.runtime_overlay:
                self.runtime_overlay.set_paused(True)
            print("Bot PAUSED")
        elif self.state == 'PAUSED':
            self.state = 'RUNNING'
            self.bot_api._paused = False
            if self.runtime_overlay:
                self.runtime_overlay.set_paused(False)
            print("Bot RESUMED")

    def restart(self):
        """Restart bot execution."""
        print("\nRestarting bot...")
        self.state = 'STOPPED'
        
        # Reset components
        if self.script_interpreter:
            self.script_interpreter.stop()
        
        time.sleep(0.5)
        
        # Restart
        self.state = 'RUNNING'
        self.bot_api.reset_state()
        self.script_thread = threading.Thread(target=self._script_loop, daemon=True)
        self.script_thread.start()
        
        print("Bot restarted.")

    def stop(self):
        """Stop the bot gracefully."""
        print("\nStopping bot...")
        self.state = 'STOPPED'
        
        # Stop script
        if self.script_interpreter:
            self.script_interpreter.stop()
        
        # Stop overlay
        if self.runtime_overlay:
            self.runtime_overlay.stop()
        
        # Stop vision pipeline
        if self.vision_pipeline:
            self.vision_pipeline.stop()
        
        # Stop capture engine
        if self.capture_engine:
            self.capture_engine.stop()
        
        print("Bot stopped.")

    def run(self, script_path: str = None, process_name: str = None):
        """
        Run the complete bot workflow.
        
        Args:
            script_path: Path to bot script file.
            process_name: Target game process name.
        """
        try:
            # Initialize
            self.initialize()
            
            # Select process
            if not self.select_process(process_name):
                print("No process selected. Exiting.")
                return
            
            # Load script
            if script_path and not self.load_script(script_path):
                print("Failed to load script. Exiting.")
                return
            
            # Configure
            if not self.configure():
                print("Configuration failed. Exiting.")
                return
            
            # Start
            self.start()
            
            # Keep main thread alive
            while self.state != 'STOPPED':
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
            self.stop()
        except Exception as e:
            print(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()
            self.stop()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='General-Purpose PC Game Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --script examples/bot_script.txt --process "GameName"
  python main.py  # Interactive mode
        """
    )
    
    parser.add_argument(
        '--script', '-s',
        type=str,
        help='Path to bot script file'
    )
    
    parser.add_argument(
        '--process', '-p',
        type=str,
        help='Target game process name'
    )
    
    parser.add_argument(
        '--pid',
        type=int,
        help='Target game process PID'
    )
    
    args = parser.parse_args()
    
    # Create and run bot
    bot = GameBot()
    
    if args.pid:
        bot.run(script_path=args.script, process_name=None)
        bot.process_manager.select_process(pid=args.pid)
    else:
        bot.run(script_path=args.script, process_name=args.process)


if __name__ == '__main__':
    main()
