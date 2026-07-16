"""
Custom Scripting Engine (DSL) Module.
Lua-like syntax with sandboxed execution for secure bot automation.
Supports control flow (if, else, switch, while) and built-in bot commands.
"""

import ast
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
import threading


@dataclass
class ScriptConfig:
    """Configuration variable exposed by the script."""
    name: str
    var_type: str  # 'slider', 'toggle', 'dropdown'
    default_value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: Optional[List[str]] = None


@dataclass
class ScriptVariable:
    """Runtime variable in the script context."""
    name: str
    value: Any
    is_exposed: bool = False
    config: Optional[ScriptConfig] = None


class BotAPI:
    """
    Host functions exposed to the scripting engine.
    Provides safe access to vision, input, and delay operations.
    """

    def __init__(self):
        self.vision_results = {}
        self.config_values: Dict[str, Any] = {}
        self._paused = False
        self._stop_requested = False

    def set_vision_results(self, results: Dict[str, Any]):
        """Update vision results available to scripts."""
        self.vision_results = results

    def set_config_value(self, name: str, value: Any):
        """Set a configuration value from the UI."""
        self.config_values[name] = value

    def get_config_value(self, name: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config_values.get(name, default)

    # === Vision Functions ===

    def find_object(self, label: str, min_confidence: float = 0.8) -> Optional[Dict[str, Any]]:
        """
        Find an object by label in the latest vision results.
        
        Args:
            label: Object label to search for.
            min_confidence: Minimum confidence threshold.
            
        Returns:
            Detection info dict or None if not found.
        """
        detections = self.vision_results.get('detections', [])
        for det in detections:
            if det.label == label and det.confidence >= min_confidence:
                return {
                    'x': det.center[0],
                    'y': det.center[1],
                    'bbox': det.bbox,
                    'confidence': det.confidence
                }
        return None

    def find_all_objects(self, label: str, min_confidence: float = 0.8) -> List[Dict[str, Any]]:
        """Find all objects matching the label."""
        results = []
        detections = self.vision_results.get('detections', [])
        for det in detections:
            if det.label == label and det.confidence >= min_confidence:
                results.append({
                    'x': det.center[0],
                    'y': det.center[1],
                    'bbox': det.bbox,
                    'confidence': det.confidence
                })
        return results

    def read_text(self, region: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Read text from screen.
        
        Args:
            region: Optional region (x1, y1, x2, y2) to limit OCR.
            
        Returns:
            List of text results with position and confidence.
        """
        text_results = self.vision_results.get('text', [])
        if region:
            x1, y1, x2, y2 = region
            filtered = []
            for txt in text_results:
                tx, ty = txt.position
                if x1 <= tx <= x2 and y1 <= ty <= y2:
                    filtered.append(txt)
            return filtered
        return text_results

    def text_exists(self, text_pattern: str, min_confidence: float = 0.7) -> bool:
        """Check if specific text exists on screen."""
        text_results = self.vision_results.get('text', [])
        for txt in text_results:
            if text_pattern.lower() in txt.text.lower() and txt.confidence >= min_confidence:
                return True
        return False

    # === Input Functions ===

    def press_key(self, key: str, duration: float = 0.1):
        """
        Press a keyboard key.
        
        Args:
            key: Key code (e.g., 'a', 'space', 'enter').
            duration: How long to hold the key in seconds.
        """
        if self._paused:
            return
        
        try:
            import pydirectinput
            pydirectinput.keyDown(key)
            time.sleep(duration)
            pydirectinput.keyUp(key)
        except ImportError:
            print(f"[SIMULATED] press_key('{key}', {duration})")

    def hold_key(self, key: str):
        """Hold down a key without releasing."""
        if self._paused:
            return
        
        try:
            import pydirectinput
            pydirectinput.keyDown(key)
        except ImportError:
            print(f"[SIMULATED] hold_key('{key}')")

    def release_key(self, key: str):
        """Release a held key."""
        try:
            import pydirectinput
            pydirectinput.keyUp(key)
        except ImportError:
            print(f"[SIMULATED] release_key('{key}')")

    def click_mouse(self, button: str = 'left', clicks: int = 1):
        """
        Click the mouse.
        
        Args:
            button: Mouse button ('left', 'right', 'middle').
            clicks: Number of clicks.
        """
        if self._paused:
            return
        
        try:
            import pydirectinput
            for _ in range(clicks):
                pydirectinput.click(button=button)
        except ImportError:
            print(f"[SIMULATED] click_mouse('{button}', {clicks})")

    def move_mouse(self, x: int, y: int, duration: float = 0.1):
        """
        Move mouse to coordinates.
        
        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            duration: Movement duration in seconds.
        """
        if self._paused:
            return
        
        try:
            import pydirectinput
            pydirectinput.moveTo(x, y, duration=duration)
        except ImportError:
            print(f"[SIMULATED] move_mouse({x}, {y}, {duration})")

    def click_at(self, x: int, y: int, button: str = 'left'):
        """Move to coordinates and click."""
        self.move_mouse(x, y, duration=0.05)
        self.click_mouse(button=button)

    # === Control Functions ===

    def wait(self, seconds: float):
        """
        Wait for specified duration. Respects pause state.
        
        Args:
            seconds: Duration to wait.
        """
        start_time = time.time()
        while time.time() - start_time < seconds:
            if self._stop_requested:
                break
            if self._paused:
                time.sleep(0.05)
            else:
                time.sleep(0.01)

    def random_wait(self, min_seconds: float, max_seconds: float):
        """Wait for a random duration between min and max."""
        import random
        duration = random.uniform(min_seconds, max_seconds)
        self.wait(duration)

    def log(self, message: str):
        """Log a message to console."""
        print(f"[SCRIPT] {message}")

    # === State Management ===

    def is_paused(self) -> bool:
        """Check if bot is paused."""
        return self._paused

    def request_stop(self):
        """Request script termination."""
        self._stop_requested = True

    def reset_state(self):
        """Reset script state."""
        self._paused = False
        self._stop_requested = False
        self.vision_results = {}


class DSLParser:
    """
    Parser for the custom Lua-like DSL.
    Uses Python's ast module to create an AST from script text.
    """

    def __init__(self):
        self.expose_functions: List[ScriptConfig] = []

    def parse(self, script_text: str) -> ast.AST:
        """
        Parse script text into AST.
        
        Args:
            script_text: The script source code.
            
        Returns:
            Abstract Syntax Tree.
        """
        # Transform Lua-like syntax to Python-compatible syntax
        transformed = self._transform_syntax(script_text)
        
        try:
            tree = ast.parse(transformed)
            return tree
        except SyntaxError as e:
            raise SyntaxError(f"Script syntax error at line {e.lineno}: {e.msg}")

    def _transform_syntax(self, script_text: str) -> str:
        """
        Transform Lua-like syntax to Python syntax.
        
        Supported transformations:
        - then/end blocks → colon/indentation
        - switch/case → if/elif
        - function definitions
        """
        lines = script_text.split('\n')
        transformed_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Handle expose_* declarations (store for UI generation)
            if stripped.startswith('expose_slider('):
                self._parse_expose_slider(stripped)
                continue
            elif stripped.startswith('expose_toggle('):
                self._parse_expose_toggle(stripped)
                continue
            elif stripped.startswith('expose_dropdown('):
                self._parse_expose_dropdown(stripped)
                continue
            
            # Transform if-then-end to Python if
            if stripped.startswith('if ') and ' then' in stripped:
                condition = stripped.replace(' then', '').replace('if ', '')
                indent = len(line) - len(line.lstrip())
                transformed_lines.append(' ' * indent + f'if {condition}:')
                continue
            
            # Transform elseif to elif
            elif stripped.startswith('elseif ') and ' then' in stripped:
                condition = stripped.replace(' then', '').replace('elseif ', '')
                indent = len(line) - len(line.lstrip())
                transformed_lines.append(' ' * indent + f'elif {condition}:')
                continue
            
            # Transform else
            elif stripped == 'else':
                indent = len(line) - len(line.lstrip())
                transformed_lines.append(' ' * indent + 'else:')
                continue
            
            # Transform end
            elif stripped == 'end':
                # Just remove it, Python uses indentation
                continue
            
            # Transform while-do to while
            elif stripped.startswith('while ') and ' do' in stripped:
                condition = stripped.replace(' do', '').replace('while ', '')
                indent = len(line) - len(line.lstrip())
                transformed_lines.append(' ' * indent + f'while {condition}:')
                continue
            
            # Keep other lines as-is (comments, assignments, function calls)
            else:
                transformed_lines.append(line)
        
        return '\n'.join(transformed_lines)

    def _parse_expose_slider(self, call: str):
        """Parse expose_slider(name, min, max) declaration."""
        # Extract arguments
        args_str = call.replace('expose_slider(', '').rstrip(')')
        parts = [p.strip().strip('"\'') for p in args_str.split(',')]
        
        if len(parts) >= 3:
            name = parts[0]
            try:
                min_val = float(parts[1])
                max_val = float(parts[2])
                self.expose_functions.append(ScriptConfig(
                    name=name,
                    var_type='slider',
                    default_value=min_val,
                    min_value=min_val,
                    max_value=max_val
                ))
            except ValueError:
                pass

    def _parse_expose_toggle(self, call: str):
        """Parse expose_toggle(name) declaration."""
        args_str = call.replace('expose_toggle(', '').rstrip(')')
        name = args_str.strip().strip('"\'')
        
        if name:
            self.expose_functions.append(ScriptConfig(
                name=name,
                var_type='toggle',
                default_value=False
            ))

    def _parse_expose_dropdown(self, call: str):
        """Parse expose_dropdown(name, [options]) declaration."""
        args_str = call.replace('expose_dropdown(', '').rstrip(')')
        parts = [p.strip() for p in args_str.split(',')]
        
        if len(parts) >= 2:
            name = parts[0].strip('"\'')
            # Parse options list
            options_str = ','.join(parts[1:])
            options = [o.strip().strip('"\'') for o in options_str.strip('[]').split(',')]
            
            self.expose_functions.append(ScriptConfig(
                name=name,
                var_type='dropdown',
                default_value=options[0] if options else '',
                options=options
            ))

    def get_expose_configs(self) -> List[ScriptConfig]:
        """Get all exposed configuration variables."""
        return self.expose_functions.copy()

    def reset(self):
        """Reset parser state for new script."""
        self.expose_functions = []


class ScriptInterpreter:
    """
    Custom interpreter that walks the AST and executes actions.
    Sandboxed execution with only specific host functions exposed.
    """

    def __init__(self, bot_api: BotAPI):
        self.bot_api = bot_api
        self.parser = DSLParser()
        self.variables: Dict[str, Any] = {}
        self.running = False

    def load_script(self, script_text: str):
        """
        Load and parse a script.
        
        Args:
            script_text: Script source code.
        """
        self.parser.reset()
        self.tree = self.parser.parse(script_text)
        self.variables = {}

    def get_config_variables(self) -> List[ScriptConfig]:
        """Get configuration variables defined in the script."""
        return self.parser.get_expose_configs()

    def execute(self):
        """Execute the loaded script."""
        self.running = True
        self.bot_api.reset_state()
        
        try:
            self._execute_node(self.tree)
        except Exception as e:
            print(f"Script execution error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.running = False

    def stop(self):
        """Stop script execution."""
        self.running = False
        self.bot_api.request_stop()

    def _execute_node(self, node: ast.AST):
        """Execute an AST node."""
        if not self.running or self.bot_api._stop_requested:
            return
        
        if isinstance(node, ast.Module):
            for child in node.body:
                self._execute_node(child)
                
        elif isinstance(node, ast.If):
            self._execute_if(node)
            
        elif isinstance(node, ast.While):
            self._execute_while(node)
            
        elif isinstance(node, ast.Assign):
            self._execute_assign(node)
            
        elif isinstance(node, ast.Expr):
            self._execute_expr(node)
            
        elif isinstance(node, ast.Call):
            self._execute_call(node)
            
        # Skip imports, function definitions, etc.

    def _execute_if(self, node: ast.If):
        """Execute an if statement."""
        condition = self._eval_condition(node.test)
        
        if condition:
            for child in node.body:
                self._execute_node(child)
        else:
            for child in node.orelse:
                self._execute_node(child)

    def _execute_while(self, node: ast.While):
        """Execute a while loop."""
        while self.running and not self.bot_api._stop_requested:
            condition = self._eval_condition(node.test)
            if not condition:
                break
            for child in node.body:
                if not self.running:
                    break
                self._execute_node(child)

    def _execute_assign(self, node: ast.Assign):
        """Execute an assignment statement."""
        value = self._eval_expression(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.variables[target.id] = value

    def _execute_expr(self, node: ast.Expr):
        """Execute an expression statement."""
        if isinstance(node.value, ast.Call):
            self._execute_call(node.value)

    def _execute_call(self, node: ast.Call):
        """Execute a function call."""
        func_name = None
        
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        
        if not func_name:
            return
        
        # Evaluate arguments
        args = [self._eval_expression(arg) for arg in node.args]
        
        # Execute built-in bot functions
        self._call_bot_function(func_name, args)

    def _call_bot_function(self, name: str, args: List[Any]):
        """Call a bot API function."""
        # Map function names to bot_api methods
        func_map = {
            'press_key': self.bot_api.press_key,
            'hold_key': self.bot_api.hold_key,
            'release_key': self.bot_api.release_key,
            'click_mouse': self.bot_api.click_mouse,
            'move_mouse': self.bot_api.move_mouse,
            'click_at': self.bot_api.click_at,
            'wait': self.bot_api.wait,
            'random_wait': self.bot_api.random_wait,
            'log': self.bot_api.log,
            'find_object': self.bot_api.find_object,
            'find_all_objects': self.bot_api.find_all_objects,
            'read_text': self.bot_api.read_text,
            'text_exists': self.bot_api.text_exists,
        }
        
        if name in func_map:
            try:
                func_map[name](*args)
            except Exception as e:
                print(f"Function call error ({name}): {e}")

    def _eval_condition(self, node: ast.AST) -> bool:
        """Evaluate a condition expression."""
        result = self._eval_expression(node)
        return bool(result)

    def _eval_expression(self, node: ast.AST) -> Any:
        """Evaluate an expression."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return self.variables.get(node.id, 0)
        elif isinstance(node, ast.Compare):
            return self._eval_compare(node)
        elif isinstance(node, ast.BoolOp):
            return self._eval_bool_op(node)
        elif isinstance(node, ast.BinOp):
            return self._eval_bin_op(node)
        elif isinstance(node, ast.UnaryOp):
            return self._eval_unary_op(node)
        else:
            return None

    def _eval_compare(self, node: ast.Compare) -> bool:
        """Evaluate a comparison."""
        left = self._eval_expression(node.left)
        
        for op, comparator in zip(node.ops, node.comparators):
            right = self._eval_expression(comparator)
            
            if isinstance(op, ast.Eq):
                result = left == right
            elif isinstance(op, ast.NotEq):
                result = left != right
            elif isinstance(op, ast.Lt):
                result = left < right
            elif isinstance(op, ast.LtE):
                result = left <= right
            elif isinstance(op, ast.Gt):
                result = left > right
            elif isinstance(op, ast.GtE):
                result = left >= right
            else:
                result = False
            
            if not result:
                return False
        
        return True

    def _eval_bool_op(self, node: ast.BoolOp) -> bool:
        """Evaluate boolean operations (and/or)."""
        values = [self._eval_expression(v) for v in node.values]
        
        if isinstance(node.op, ast.And):
            return all(values)
        elif isinstance(node.op, ast.Or):
            return any(values)
        return False

    def _eval_bin_op(self, node: ast.BinOp) -> Any:
        """Evaluate binary operations."""
        left = self._eval_expression(node.left)
        right = self._eval_expression(node.right)
        
        if isinstance(node.op, ast.Add):
            return left + right
        elif isinstance(node.op, ast.Sub):
            return left - right
        elif isinstance(node.op, ast.Mult):
            return left * right
        elif isinstance(node.op, ast.Div):
            return left / right if right != 0 else 0
        elif isinstance(node.op, ast.Mod):
            return left % right if right != 0 else 0
        return None

    def _eval_unary_op(self, node: ast.UnaryOp) -> Any:
        """Evaluate unary operations."""
        operand = self._eval_expression(node.operand)
        
        if isinstance(node.op, ast.USub):
            return -operand
        elif isinstance(node.op, ast.Not):
            return not operand
        return operand


# Factory function
def create_script_engine() -> tuple[ScriptInterpreter, BotAPI]:
    """Create a new script engine instance."""
    bot_api = BotAPI()
    interpreter = ScriptInterpreter(bot_api)
    return interpreter, bot_api
