# Template Matching Guide

## Overview

This game bot uses **template matching** for object detection instead of YOLO or other neural network models. This approach is:

- ✅ **Lightweight**: No GPU required, minimal CPU usage
- ✅ **Simple**: Just add images to a folder
- ✅ **Accurate**: Perfect for UI elements, icons, and static game objects
- ✅ **Fast**: Multi-scale matching runs efficiently in parallel threads

## How It Works

1. You provide template images (screenshots of objects you want to detect)
2. The bot loads these templates from the `assets/templates/` folder
3. During runtime, it searches the screen for matches using OpenCV's template matching
4. When a match is found with sufficient confidence, it returns the coordinates

## Setting Up Templates

### Step 1: Create Template Images

1. **Take a screenshot** of the object you want to detect while the game is running
   - Use Print Screen, or a tool like ShareX, Greenshot, etc.
   
2. **Crop the image** to show only the target object
   - Use any image editor (Paint, Photoshop, GIMP, etc.)
   - Crop tightly around the object
   - Avoid including unnecessary background

3. **Save the image** in the `assets/templates/` folder
   - Supported formats: PNG, JPG, JPEG, BMP, WEBP
   - PNG recommended for lossless quality
   - Keep file size reasonable (< 500KB typically)

### Step 2: Naming Convention

The filename (without extension) becomes the **label** used in your scripts:

| Filename | Script Label | Example Usage |
|----------|--------------|---------------|
| `enemy.png` | `"enemy"` | `find_object("enemy", 0.75)` |
| `health_potion.jpg` | `"health_potion"` | `find_object("health_potion", 0.8)` |
| `minimap.bmp` | `"minimap"` | `find_object("minimap", 0.9)` |
| `loot_chest.png` | `"loot_chest"` | `find_all_objects("loot_chest", 0.7)` |

### Step 3: Using in Scripts

```lua
-- Find a single enemy
enemy = find_object("enemy", 0.75)

if enemy then
    log("Enemy found at " .. enemy.x .. ", " .. enemy.y)
    click_at(enemy.x, enemy.y, "left")
end

-- Find all loot items
loot_items = find_all_objects("loot_item", 0.8)

for i, loot in ipairs(loot_items) do
    log("Loot #" .. i .. " at " .. loot.x .. ", " .. loot.y)
    click_at(loot.x, loot.y, "right")
    wait(0.3)
end
```

## Advanced Tips

### Multiple Templates for Same Object

You can have multiple template files with the same base name to handle variations:

```
assets/templates/
├── enemy.png          # Front view
├── enemy_side.png     # Side view (rename to enemy.png if needed)
└── enemy_back.png     # Back view (rename to enemy.png if needed)
```

Actually, to have multiple templates for the same label, name them identically but place in subdirectories:

```
assets/templates/
├── enemy_front.png
├── enemy_side.png
└── enemy_back.png
```

Then use `find_object("enemy_front", 0.75)`, etc., or better yet, use different labels for different views.

For true multi-template matching (all files named "enemy" in different folders):
```
assets/templates/
├── variant1/enemy.png
├── variant2/enemy.png
└── variant3/enemy.png
```

The system will load all three and test each when searching for "enemy".

### Multi-Scale Detection

The bot automatically tests templates at multiple scales:
- 100%, 90%, 80%, 70%, 60%, 50%, 40%, 30%

This means you don't need to create multiple sizes of the same template. The system handles size variations automatically.

### Confidence Thresholds

The confidence threshold determines how strict the matching should be:

| Threshold | Behavior | Use Case |
|-----------|----------|----------|
| 0.9 - 1.0 | Very strict | Critical UI elements, exact matches |
| 0.75 - 0.9 | Balanced (recommended) | Most game objects, enemies, items |
| 0.5 - 0.75 | Lenient | Variable appearances, degraded graphics |
| < 0.5 | Too lenient | Not recommended (false positives) |

**Start with 0.75** and adjust based on results:
- If missing detections → lower threshold
- If false positives → raise threshold

### Performance Optimization

1. **Keep templates small**: 50x50 to 200x200 pixels is usually sufficient
2. **Use fewer templates**: Each template adds processing time
3. **Disable OCR if not needed**: Set `enable_ocr=False` in initialization
4. **Organize with subdirectories**: Helps manage large template collections

```
assets/templates/
├── combat/
│   ├── enemy_warrior.png
│   ├── enemy_mage.png
│   └── boss.png
├── items/
│   ├── health_potion.png
│   ├── mana_potion.png
│   └── gold_coin.png
└── ui/
    ├── minimap.png
    ├── health_bar.png
    └── quest_marker.png
```

## Troubleshooting

### Objects Not Detected

**Problem**: `find_object()` always returns `nil`

**Solutions**:
1. Verify template exists in `assets/templates/` folder
2. Check console output for "Loaded template" messages
3. Ensure template filename matches the label in script (case-sensitive)
4. Lower the confidence threshold (try 0.6)
5. Verify the object actually appears on screen during testing
6. Make sure template image quality matches in-game appearance

### False Positives

**Problem**: Detecting objects that aren't there

**Solutions**:
1. Raise the confidence threshold (try 0.85 or higher)
2. Improve template quality (clearer, more distinctive image)
3. Add more unique features to the template crop
4. Reduce the number of scale levels if needed

### Poor Performance

**Problem**: Bot is slow or CPU usage is high

**Solutions**:
1. Reduce number of templates
2. Make template images smaller
3. Disable OCR: `enable_ocr=False`
4. Reduce capture FPS if possible

## Example Workflow

Let's create a complete example for detecting enemies and loot:

### 1. Capture Templates

```bash
# In your game:
# 1. Find an enemy, take screenshot
# 2. Crop to enemy icon, save as enemy.png
# 3. Find a loot item, take screenshot  
# 4. Crop to loot icon, save as loot_item.png
# 5. Copy both to assets/templates/
```

### 2. Folder Structure

```
workspace/
├── assets/
│   └── templates/
│       ├── enemy.png      # Your enemy template
│       └── loot_item.png  # Your loot template
├── examples/
│   └── bot_script.txt
└── main.py
```

### 3. Script

```lua
-- Configuration
expose_slider("detection_confidence", 0.6, 0.9)

log("Starting farming bot...")

while true do
    -- Look for enemies
    enemy = find_object("enemy", get_config_value("detection_confidence", 0.75))
    
    if enemy then
        log("Enemy detected! Attacking...")
        click_at(enemy.x, enemy.y, "left")
        press_key("space", 0.2)
        wait(1.0)
    else
        -- No enemy, look for loot
        loot = find_object("loot_item", 0.8)
        
        if loot then
            log("Loot found! Collecting...")
            click_at(loot.x, loot.y, "right")
            wait(0.5)
        else
            -- Nothing found, wait and retry
            random_wait(0.5, 1.0)
        end
    end
    
    wait(0.1)
end
```

### 4. Run the Bot

```bash
python main.py --script examples/bot_script.txt --process "YourGame.exe"
```

Check the console output to verify templates loaded correctly:
```
✓ Loaded template: 'enemy' from assets/templates/enemy.png ((64, 64))
✓ Loaded template: 'loot_item' from assets/templates/loot_item.png ((48, 48))

✓ Successfully loaded 2 template(s)
```

## Migration from YOLO

If you were planning to use YOLO or have existing YOLO models:

| YOLO Approach | Template Matching Equivalent |
|---------------|------------------------------|
| Train model on enemy class | Create enemy.png template |
| Adjust model confidence | Adjust `min_confidence` parameter |
| Model inference time | Near-instant template matching |
| GPU required | CPU only |
| Complex setup | Drop images in folder |

**Benefits of switching to template matching:**
- No training required
- No GPU dependency
- No ONNX runtime installation
- Easier to update (just replace image files)
- More predictable for static game elements

**When to consider alternatives:**
- Objects with many random variations
- Highly deformable objects
- Need to detect thousands of different classes

For most game bots targeting specific UI elements, icons, or character types, template matching is the superior choice.
