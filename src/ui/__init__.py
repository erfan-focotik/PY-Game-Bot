"""
User Interface Module.
Phase 1: Configuration Window (Tkinter/CustomTkinter)
Phase 2: Runtime Overlay (Dear ImGui)
"""

import threading
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass


@dataclass
class UIState:
    """UI state management."""
    is_running: bool = False
    is_paused: bool = False
    script_loaded: bool = False
    script_path: str = ""
    config_values: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config_values is None:
            self.config_values = {}


class ConfigWindow:
    """
    Phase 1: Configuration Window using CustomTkinter.
    Dynamically generates widgets based on expose_* declarations in the script.
    """

    def __init__(self, config_vars: List[Dict[str, Any]], on_confirm: Callable):
        """
        Initialize configuration window.
        
        Args:
            config_vars: List of configuration variable definitions.
            on_confirm: Callback function when user confirms settings.
        """
        self.config_vars = config_vars
        self.on_confirm = on_confirm
        self.result_values: Dict[str, Any] = {}
        self.window = None
        self.widgets: Dict[str, Any] = {}

    def show(self):
        """Show the configuration window (blocking)."""
        try:
            import customtkinter as ctk
            
            # Configure appearance
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            
            # Create window
            self.window = ctk.CTk()
            self.window.title("Bot Configuration")
            self.window.geometry("500x600")
            self.window.resizable(False, False)
            
            # Create scrollable frame
            scroll_frame = ctk.CTkScrollableFrame(self.window, width=480, height=500)
            scroll_frame.pack(pady=10, padx=10, fill="both", expand=True)
            
            # Generate widgets for each config variable
            y_offset = 10
            for var in self.config_vars:
                self._create_widget(scroll_frame, var, y_offset)
                y_offset += 80
            
            # Confirm button
            confirm_btn = ctk.CTkButton(
                self.window,
                text="Start Bot",
                command=self._on_confirm,
                height=40,
                font=("Arial", 16, "bold")
            )
            confirm_btn.pack(pady=10, padx=20, fill="x")
            
            # Center window
            self.window.update_idletasks()
            x = (self.window.winfo_screenwidth() - self.window.winfo_width()) // 2
            y = (self.window.winfo_screenheight() - self.window.winfo_height()) // 2
            self.window.geometry(f"+{x}+{y}")
            
            # Run mainloop (blocking)
            self.window.mainloop()
            
            return self.result_values
            
        except ImportError:
            print("CustomTkinter not installed. Using fallback console input.")
            return self._console_fallback()

    def _create_widget(self, parent, var_def: Dict[str, Any], y_offset: int):
        """Create appropriate widget for config variable type."""
        import customtkinter as ctk
        
        var_type = var_def.get('var_type', 'slider')
        name = var_def.get('name', 'unknown')
        default = var_def.get('default_value', 0)
        
        # Label
        label = ctk.CTkLabel(
            parent,
            text=name.replace('_', ' ').title(),
            font=("Arial", 14, "bold"),
            anchor="w"
        )
        label.pack(pady=(10, 5), padx=10, fill="x")
        
        if var_type == 'slider':
            min_val = var_def.get('min_value', 0)
            max_val = var_def.get('max_value', 100)
            
            slider_var = ctk.StringVar(value=str(default))
            
            slider = ctk.CTkSlider(
                parent,
                from_=min_val,
                to=max_val,
                number_of_steps=int(max_val - min_val),
                command=lambda v: slider_var.set(str(int(v))),
                width=400
            )
            slider.set(default)
            slider.pack(padx=10, fill="x")
            
            value_label = ctk.CTkLabel(
                parent,
                textvariable=slider_var,
                font=("Arial", 12),
                anchor="center"
            )
            value_label.pack()
            
            self.widgets[name] = {
                'type': 'slider',
                'widget': slider,
                'label': value_label,
                'string_var': slider_var
            }
            
        elif var_type == 'toggle':
            toggle_var = ctk.BooleanVar(value=default)
            
            toggle = ctk.CTkSwitch(
                parent,
                text="Enabled" if default else "Disabled",
                variable=toggle_var,
                command=lambda: toggle.configure(
                    text="Enabled" if toggle_var.get() else "Disabled"
                ),
                width=200
            )
            toggle.pack(pady=5)
            
            self.widgets[name] = {
                'type': 'toggle',
                'widget': toggle,
                'bool_var': toggle_var
            }
            
        elif var_type == 'dropdown':
            options = var_def.get('options', [])
            dropdown_var = ctk.StringVar(value=default)
            
            dropdown = ctk.CTkOptionMenu(
                parent,
                variable=dropdown_var,
                values=options,
                width=300
            )
            dropdown.pack(pady=5)
            
            self.widgets[name] = {
                'type': 'dropdown',
                'widget': dropdown,
                'string_var': dropdown_var
            }

    def _on_confirm(self):
        """Handle confirm button click."""
        # Collect all values
        for name, widget_info in self.widgets.items():
            if widget_info['type'] == 'slider':
                self.result_values[name] = int(float(widget_info['string_var'].get()))
            elif widget_info['type'] == 'toggle':
                self.result_values[name] = widget_info['bool_var'].get()
            elif widget_info['type'] == 'dropdown':
                self.result_values[name] = widget_info['string_var'].get()
        
        # Close window
        if self.window:
            self.window.destroy()
        
        # Call callback
        if self.on_confirm:
            self.on_confirm(self.result_values)

    def _console_fallback(self) -> Dict[str, Any]:
        """Fallback when GUI libraries are not available."""
        print("\n=== Bot Configuration (Console Mode) ===")
        for var in self.config_vars:
            name = var.get('name', 'unknown')
            var_type = var.get('var_type', 'slider')
            default = var.get('default_value', 0)
            
            if var_type == 'slider':
                min_val = var.get('min_value', 0)
                max_val = var.get('max_value', 100)
                value = input(f"{name} [{min_val}-{max_val}, default: {default}]: ")
                self.result_values[name] = float(value) if value else default
                
            elif var_type == 'toggle':
                value = input(f"{name} [y/n, default: {'y' if default else 'n'}]: ")
                if value.lower() == 'y':
                    self.result_values[name] = True
                elif value.lower() == 'n':
                    self.result_values[name] = False
                else:
                    self.result_values[name] = default
                    
            elif var_type == 'dropdown':
                options = var.get('options', [])
                print(f"{name}: {', '.join(options)}")
                value = input(f"Select option [default: {default}]: ")
                self.result_values[name] = value if value else default
        
        return self.result_values


class RuntimeOverlay:
    """
    Phase 2: In-Game Overlay using Dear ImGui.
    Transparent, click-through overlay with minimal controls.
    """

    def __init__(self, on_pause: Callable, on_restart: Callable, on_quit: Callable):
        """
        Initialize runtime overlay.
        
        Args:
            on_pause: Callback for pause button.
            on_restart: Callback for restart button.
            on_quit: Callback for quit button.
        """
        self.on_pause = on_pause
        self.on_restart = on_restart
        self.on_quit = on_quit
        self.running = False
        self.overlay_thread = None
        self.is_paused = False

    def start(self):
        """Start the overlay rendering thread."""
        self.running = True
        self.overlay_thread = threading.Thread(target=self._render_loop, daemon=True)
        self.overlay_thread.start()
        print("Runtime overlay started")

    def stop(self):
        """Stop the overlay."""
        self.running = False
        if self.overlay_thread:
            self.overlay_thread.join(timeout=2.0)
        print("Runtime overlay stopped")

    def set_paused(self, paused: bool):
        """Update pause state."""
        self.is_paused = paused

    def _render_loop(self):
        """Main rendering loop using Dear ImGui."""
        try:
            import imgui
            import glfw
            from imgui.integrations.glfw import GlfwRenderer
            
            # Initialize GLFW
            if not glfw.init():
                print("Failed to initialize GLFW")
                return
            
            # Create transparent window
            glfw.window_hint(glfw.VISIBLE, glfw.TRUE)
            glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, glfw.TRUE)
            glfw.window_hint(glfw.FLOATING, glfw.TRUE)
            glfw.window_hint(glfw.MOUSE_PASSTHROUGH, glfw.TRUE)
            
            window = glfw.create_window(300, 150, "Bot Overlay", None, None)
            if not window:
                print("Failed to create overlay window")
                glfw.terminate()
                return
            
            glfw.make_context_current(window)
            
            # Initialize ImGui
            imgui.create_context()
            impl = GlfwRenderer(window)
            
            # Set window position (top-right corner)
            glfw.set_window_pos(window, 1620, 20)
            
            while self.running:
                # Poll events
                glfw.poll_events()
                
                # Check if window should close
                if glfw.window_should_close(window):
                    break
                
                # Start frame
                impl.process_inputs()
                imgui.new_frame()
                
                # Toggle mouse passthrough based on hover
                io = imgui.get_io()
                if io.want_capture_mouse:
                    glfw.set_input_mode(window, glfw.MOUSE_PASSTHROUGH, glfw.FALSE)
                else:
                    glfw.set_input_mode(window, glfw.MOUSE_PASSTHROUGH, glfw.TRUE)
                
                # Render overlay UI
                imgui.set_next_window_position(0, 0)
                imgui.set_next_window_size(300, 150)
                imgui.set_next_window_bg_alpha(0.3)
                
                flags = (
                    imgui.WINDOW_NO_TITLE_BAR |
                    imgui.WINDOW_NO_RESIZE |
                    imgui.WINDOW_NO_MOVE |
                    imgui.WINDOW_NO_SCROLLBAR |
                    imgui.WINDOW_ALWAYS_AUTO_RESIZE
                )
                
                imgui.begin("Bot Controls", flags=flags)
                
                # Status indicator
                status_text = "PAUSED" if self.is_paused else "RUNNING"
                status_color = (1.0, 0.0, 0.0) if self.is_paused else (0.0, 1.0, 0.0)
                imgui.text_colored(status_text, *status_color)
                
                imgui.separator()
                
                # Control buttons
                if imgui.button("⏯ Pause/Resume", width=120, height=30):
                    if self.on_pause:
                        self.on_pause()
                
                imgui.same_line()
                
                if imgui.button("🔄 Restart", width=100, height=30):
                    if self.on_restart:
                        self.on_restart()
                
                imgui.same_line()
                
                if imgui.button("❌ Quit", width=60, height=30):
                    if self.on_quit:
                        self.on_quit()
                
                # FPS counter
                imgui.text(f"FPS: {imgui.get_io().framerate:.0f}")
                
                imgui.end()
                
                # Render
                imgui.render()
                impl.render(imgui.get_draw_data())
                glfw.swap_buffers(window)
                
                time.sleep(0.016)  # ~60 FPS
            
            # Cleanup
            impl.shutdown()
            glfw.terminate()
            
        except ImportError:
            print("Dear ImGui or GLFW not available. Overlay disabled.")
            # Fallback: simple console-based control
            self._console_control_loop()
        except Exception as e:
            print(f"Overlay error: {e}")

    def _console_control_loop(self):
        """Fallback console-based control when ImGui is not available."""
        print("\n=== Runtime Controls (Console Mode) ===")
        print("Press ENTER to Pause/Resume")
        print("Type 'restart' and press ENTER to restart")
        print("Type 'quit' and press ENTER to exit")
        
        while self.running:
            try:
                cmd = input().strip().lower()
                if cmd == '':
                    if self.on_pause:
                        self.on_pause()
                elif cmd == 'restart':
                    if self.on_restart:
                        self.on_restart()
                elif cmd == 'quit':
                    if self.on_quit:
                        self.on_quit()
                    break
            except EOFError:
                break


# Factory functions
def create_config_window(config_vars: List[Dict[str, Any]], 
                         on_confirm: Callable) -> ConfigWindow:
    """Create a configuration window instance."""
    return ConfigWindow(config_vars, on_confirm)


def create_runtime_overlay(on_pause: Callable, 
                           on_restart: Callable, 
                           on_quit: Callable) -> RuntimeOverlay:
    """Create a runtime overlay instance."""
    return RuntimeOverlay(on_pause, on_restart, on_quit)
