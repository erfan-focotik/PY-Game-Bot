# General-Purpose PC Game Bot

A high-performance, Windows-based game automation tool featuring a custom secure scripting engine, hybrid computer vision pipeline, and minimalist user interface.

## Features

- **Custom Scripting Engine**: Lua-like DSL with sandboxed execution for secure bot automation
- **High-Performance Screen Capture**: DXcam/D3DShot using Windows Desktop Duplication API (>60 FPS)
- **Efficient Vision Pipeline**: 
  - Multi-scale template matching for object detection (CPU-based, lightweight)
  - PaddleOCR for text recognition (optional, can be disabled for performance)
  - No YOLO/ONNX dependencies - uses efficient template matching instead
- **Dynamic UI Configuration**: Auto-generated configuration window based on script declarations
- **In-Game Overlay**: Dear ImGui-based transparent overlay with pause/restart/quit controls
- **Process Management**: Easy target game selection by name or PID

## Project Structure

```
/workspace
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── Brief.md               # Technical specification
├── docs/
│   └── BOT_SCRIPT_REFERENCE.md  # Script language documentation
├── examples/
│   └── bot_script.txt     # Example bot script
├── src/
│   ├── capture/           # Screen capture engine (DXcam)
│   ├── vision/            # Computer vision pipeline
│   ├── scripting/         # Custom DSL parser & interpreter
│   ├── ui/                # Configuration window & runtime overlay
│   └── utils/             # Process management & utilities
├── assets/templates/      # Template images for object detection
└── configs/               # User configuration files
```

## Installation

### Prerequisites

- Windows 10/11 (64-bit)
- Python 3.9+
- Visual C++ Redistributable (for OpenCV)

### Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: Some packages are Windows-specific:
- `dxcam` - Windows screen capture
- `pydirectinput` - Low-latency input simulation

## Quick Start

### 1. Run the Bot

```bash
# Interactive mode (select process and script manually)
python main.py

# With command-line arguments
python main.py --script examples/bot_script.txt --process "GameName"
```

### 2. Workflow

1. **Select Target Process**: Choose the game window to automate
2. **Load Script**: Select your bot script file (`.txt`)
3. **Configure**: Adjust settings in the configuration window
4. **Run**: Bot starts with overlay controls available

## Scripting Language

The bot uses a custom Lua-like DSL for defining automation logic. See [`docs/BOT_SCRIPT_REFERENCE.md`](docs/BOT_SCRIPT_REFERENCE.md) for complete documentation.

### Basic Example

```lua
-- Configuration variables (appear in UI)
expose_slider("attack_delay", 0.5, 2.0)
expose_toggle("auto_loot")

-- Main bot loop
while true do
    enemy = find_object("enemy", 0.75)
    
    if enemy then
        click_at(enemy.x, enemy.y, "left")
        press_key("space", 0.2)
        wait(get_config_value("attack_delay", 1.0))
    else
        random_wait(0.5, 1.5)
    end
    
    -- OCR-based condition
    if text_exists("LOW HEALTH", 0.8) then
        press_key("1", 0.1)  -- Use health potion
    end
end
```

### Key Functions

| Category | Functions |
|----------|-----------|
| Vision | `find_object()`, `find_all_objects()`, `read_text()`, `text_exists()` |
| Input | `press_key()`, `hold_key()`, `click_mouse()`, `move_mouse()`, `click_at()` |
| Control | `wait()`, `random_wait()`, `log()` |
| Config | `get_config_value()` |

## Architecture

### Screen Capture (Producer)
- Runs in dedicated background thread
- Uses Windows Desktop Duplication API via DXcam
- Pushes frames to thread-safe queue
- Target: >60 FPS capture rate

### Vision Pipeline (Consumer)
- ThreadPoolExecutor for parallel processing
- Template matching for object detection (replaces YOLO for efficiency)
- PaddleOCR for text recognition (optional)
- Results pushed to result queue

### Scripting Engine
- Custom AST-based parser
- Sandboxed execution (no arbitrary code)
- Lua-like syntax with control flow
- Only approved host functions exposed

### User Interface
- **Phase 1**: Tkinter/CustomTkinter config window
- **Phase 2**: Dear ImGui in-game overlay
- Dynamic widget generation from script declarations

## Configuration Variables

Scripts can expose configuration variables that appear in the UI:

```lua
expose_slider("name", min, max)    -- Slider input
expose_toggle("name")              -- Checkbox
expose_dropdown("name", [opts])    -- Dropdown menu
```

## State Management

The bot supports three states:
- **RUNNING**: Normal operation
- **PAUSED**: Script halted, capture continues
- **STOPPED**: All threads terminated

Controls available via overlay or console:
- Pause/Resume
- Restart (resets script state)
- Quit (graceful shutdown)

## Performance

- Screen capture: 60+ FPS (hardware dependent)
- Vision processing: Parallelized with thread pool
- Input latency: <10ms with pydirectinput
- Memory footprint: ~200MB typical

## Security

- Sandboxed script execution
- No file system access from scripts
- No network access from scripts
- No arbitrary Python code execution
- Only whitelisted functions available

## Troubleshooting

### Common Issues

1. **Screen capture not working**
   - Ensure running as administrator
   - Check Windows Desktop Duplication support
   - Verify game is not in exclusive fullscreen

2. **Objects not detected**
   - Add template images to `assets/templates/`
   - Adjust confidence threshold
   - Check image scale variations

3. **Input not registered**
   - Run as administrator
   - Check anti-cheat compatibility
   - Ensure correct process selected

## Development

### Adding New Object Templates

Place template images in the `assets/templates/` folder:
- File naming: `<object_label>.png` (e.g., "enemy.png", "loot_item.png")
- The filename (without extension) becomes the label used in scripts
- Multiple templates with same name are all tested for that label
- Subdirectories are scanned recursively for organization

Example:
```bash
# Create template for enemy detection
# 1. Take screenshot of enemy icon in your game
# 2. Crop to just the enemy icon
# 3. Save as assets/templates/enemy.png
# 4. In script: enemy = find_object("enemy", 0.75)
```

## License

See LICENSE file.

## Contributing

1. Fork the repository
2. Create feature branch
3. Submit pull request

## Support

For issues and questions:
- Check `docs/BOT_SCRIPT_REFERENCE.md`
- Review `Brief.md` for technical details
- See example scripts in `/examples`
