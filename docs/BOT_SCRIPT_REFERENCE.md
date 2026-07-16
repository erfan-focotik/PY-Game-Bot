# Bot Script Reference Guide

## Overview

This document describes the custom Lua-like scripting language for the Game Bot automation tool. The DSL (Domain-Specific Language) provides a simple, secure way to define bot behavior without exposing the full Python environment.

---

## Script Structure

A bot script consists of:
1. **Configuration Declarations** - Variables exposed to the UI
2. **Main Logic** - Control flow and bot actions
3. **Comments** - Using `--` for single-line comments

---

## Configuration Variables

Configuration variables are declared at the top of your script and appear in the configuration window before the bot starts.

### Slider
```lua
expose_slider("variable_name", min_value, max_value)
```
Creates a slider input. Example:
```lua
expose_slider("attack_delay", 0.5, 2.0)
```

### Toggle
```lua
expose_toggle("variable_name")
```
Creates a checkbox toggle. Example:
```lua
expose_toggle("auto_loot")
```

### Dropdown
```lua
expose_dropdown("variable_name", ["option1", "option2", "option3"])
```
Creates a dropdown menu. Example:
```lua
expose_dropdown("combat_mode", ["aggressive", "defensive", "passive"])
```

---

## Vision Functions

### How Object Detection Works

The bot uses **template matching** for object detection. Here's how to set it up:

1. **Create Template Images**: 
   - Take a screenshot of the object you want to detect (enemy, item, etc.)
   - Crop the image to show only that object
   - Save it in the `assets/templates/` folder

2. **Naming Convention**:
   - The filename (without extension) becomes the object label
   - Example: `enemy.png` → use label `"enemy"` in scripts
   - Example: `health_potion.jpg` → use label `"health_potion"`

3. **Multiple Templates**:
   - You can have multiple template images with the same name
   - All templates are tested when searching for that label
   - Useful for different rotations or appearances of the same object

4. **In Your Script**:
```lua
-- Search for enemy.png template on screen
enemy = find_object("enemy", 0.75)  -- 0.75 = 75% confidence threshold

if enemy then
    log("Found enemy at: " .. enemy.x .. ", " .. enemy.y)
end
```

### find_object(label, min_confidence)
Find an object by label in the latest vision results.
```lua
enemy = find_object("enemy", 0.75)
if enemy then
    log("Found enemy at: " .. enemy.x .. ", " .. enemy.y)
end
```
Returns: `{x, y, bbox, confidence}` or `nil`

**Parameters:**
- `label`: Name of the template file (without extension)
- `min_confidence`: Match threshold from 0.0 to 1.0 (recommended: 0.7-0.9)

### find_all_objects(label, min_confidence)
Find all objects matching the label.
```lua
enemies = find_all_objects("mob", 0.7)
log("Found " .. #enemies .. " enemies")
```
Returns: Array of detection objects

### read_text(region)
Read text from screen using OCR (optional region).
```lua
texts = read_text()
for _, text in ipairs(texts) do
    log("Text: " .. text.text)
end
```
Returns: Array of `{text, confidence, bbox, position}`

**Note:** OCR can be disabled in configuration for better performance if not needed.

### text_exists(pattern, min_confidence)
Check if specific text exists on screen using OCR.
```lua
if text_exists("LOW HEALTH", 0.8) then
    press_key("1", 0.1)
end
```
Returns: `true` or `false`

---

## Input Functions

### press_key(key, duration)
Press a keyboard key.
```lua
press_key("space", 0.2)  -- Press spacebar for 0.2 seconds
press_key("enter", 0.1)
```

### hold_key(key)
Hold down a key without releasing.
```lua
hold_key("shift")  -- Hold shift key
```

### release_key(key)
Release a held key.
```lua
release_key("shift")  -- Release shift key
```

### click_mouse(button, clicks)
Click the mouse.
```lua
click_mouse("left", 1)   -- Single left click
click_mouse("right", 1)  -- Single right click
click_mouse("left", 2)   -- Double left click
```

### move_mouse(x, y, duration)
Move mouse to coordinates.
```lua
move_mouse(960, 540, 0.1)  -- Move to center over 0.1 seconds
```

### click_at(x, y, button)
Move to coordinates and click.
```lua
click_at(500, 300, "left")  -- Click at position (500, 300)
```

---

## Control Functions

### wait(seconds)
Wait for specified duration.
```lua
wait(1.5)  -- Wait 1.5 seconds
```

### random_wait(min_seconds, max_seconds)
Wait for a random duration between min and max.
```lua
random_wait(0.5, 1.5)  -- Wait between 0.5 and 1.5 seconds
```

### log(message)
Log a message to console.
```lua
log("Bot started!")
log("Health: " .. health)
```

---

## Configuration Access

### get_config_value(name, default)
Get a configuration value set in the UI.
```lua
delay = get_config_value("attack_delay", 1.0)
auto_loot = get_config_value("auto_loot", false)
mode = get_config_value("combat_mode", "passive")
```

---

## Control Flow

### If-Then-Else
```lua
if condition then
    -- code
elseif other_condition then
    -- code
else
    -- code
end
```

Example:
```lua
if enemy then
    attack()
elseif health < 30 then
    use_potion()
else
    explore()
end
```

### While Loop
```lua
while condition do
    -- code
end
```

Example:
```lua
while true do
    enemy = find_object("target", 0.8)
    if enemy then
        click_at(enemy.x, enemy.y)
    end
    wait(0.1)
end
```

---

## Operators

### Comparison
- `==` Equal
- `~=` Not equal
- `<` Less than
- `<=` Less than or equal
- `>` Greater than
- `>=` Greater than or equal

### Logical
- `and` Logical AND
- `or` Logical OR
- `not` Logical NOT

### Arithmetic
- `+` Addition
- `-` Subtraction
- `*` Multiplication
- `/` Division
- `%` Modulo

### String Concatenation
- `..` Concatenate strings
```lua
message = "Health: " .. health .. "%"
```

---

## Complete Example

```lua
-- ============================================
-- Boss Battle Bot
-- ============================================

-- Configuration
expose_slider("attack_speed", 0.3, 1.5)
expose_toggle("dodge_attacks")
expose_dropdown("strategy", ["melee", "ranged", "hybrid"])

-- Constants
HEALTH_POTION_KEY = "1"
MANA_POTION_KEY = "2"
ATTACK_KEY = "space"

log("Boss Battle Bot initialized!")

-- Main loop
while true do
    
    -- Find boss
    boss = find_object("boss", 0.8)
    
    if boss then
        -- Attack boss
        click_at(boss.x, boss.y, "left")
        wait(0.05)
        press_key(ATTACK_KEY, 0.2)
        
        -- Wait based on attack speed setting
        wait(get_config_value("attack_speed", 0.5))
        
    else
        -- Search for boss
        log("Searching for boss...")
        move_mouse(960, 540, 0.3)
        random_wait(0.5, 1.0)
    end
    
    -- Check for low health
    if text_exists("CRITICAL", 0.7) then
        log("Critical health! Using potion...")
        press_key(HEALTH_POTION_KEY, 0.1)
        wait(1.0)
    end
    
    -- Dodge mechanic (if enabled)
    if get_config_value("dodge_attacks", false) then
        if text_exists("TELEGRAPH", 0.75) then
            log("Dodging attack!")
            press_key("shift", 0.3)  -- Dodge roll
        end
    end
    
    -- Strategy-based behavior
    strategy = get_config_value("strategy", "melee")
    
    if strategy == "ranged" and boss then
        -- Keep distance in ranged mode
        move_mouse(boss.x + 300, boss.y + 300, 0.2)
    end
    
    -- Small delay
    wait(0.05)
    
end
```

---

## Best Practices

1. **Always include delays** - Prevents CPU spinning and makes behavior more human-like
2. **Use random waits** - Vary timing to avoid detection patterns
3. **Check vision results** - Always verify objects are found before acting
4. **Graceful error handling** - Use conditions to handle missing objects
5. **Comment your code** - Makes scripts easier to maintain and share

---

## Security Notes

- Scripts run in a sandboxed environment
- Only approved functions are available
- No direct file system access
- No arbitrary code execution
- No network access from scripts

---

## Troubleshooting

### Script not executing
- Check for syntax errors in the console output
- Ensure `while true do` loop is present for continuous execution
- Verify vision pipeline is detecting objects

### Objects not found
- Add template images to the appropriate folder
- Adjust confidence threshold in `find_object()`
- Check lighting and screen conditions

### Actions not performing
- Ensure game window is in focus
- Check if anti-cheat is blocking input
- Verify process selection is correct

---

## Support

For additional help, refer to:
- `Brief.md` - Technical specification
- `Full research.pdf` - In-depth implementation details
- Example scripts in `/examples` folder
