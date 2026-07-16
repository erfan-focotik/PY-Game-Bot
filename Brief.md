# General-Purpose PC Game Bot: Technical Specification & Build Brief

## 1. Project Overview
A high-performance, Windows-based game automation tool designed for real-time interaction. The application features a **custom, secure scripting engine** (Lua-like syntax), a hybrid computer vision pipeline, and a minimalist user interface. It prioritizes speed, accuracy, and a low system footprint to ensure seamless gameplay integration.

---

## 2. Core Architecture

### A. Screen Capture Engine (Producer)
*   **Objective:** Low-latency, high-FPS frame acquisition.
*   **Technology:** `DXcam` or `D3DShot` (Windows Desktop Duplication API).
*   **Implementation:** 
    *   Runs in a dedicated background thread.
    *   Captures frames as NumPy arrays.
    *   Pushes data into a thread-safe `queue.Queue`.

### B. Computer Vision Pipeline (Consumer)
*   **Objective:** Real-time detection of objects and text.
*   **Object Recognition:**
    *   **Static Targets:** Multi-scale Template Matching (`cv2.matchTemplate`) using images from user-defined folders (e.g., `/source/Boss/Target`).
    *   **Dynamic Targets:** Lightweight YOLO models (YOLOv10n/v12n via ONNX Runtime) for robust detection under varying conditions.
*   **Text Recognition (OCR):**
    *   **Engine:** PaddleOCR (ONNX version for CPU efficiency).
    *   **Pre-processing:** OpenCV-based binarization and noise reduction to enhance accuracy and speed.
*   **Implementation:** 
    *   Uses a `ThreadPoolExecutor` to process frames from the capture queue.
    *   Results are pushed to a `Result Queue` for the script engine.

### C. Custom Scripting Engine (DSL)
*   **Objective:** Secure, intuitive logic definition without exposing the full Python environment.
*   **Syntax:** Lua-like, simple control flow (`if`, `else`, `switch`, `while`), and built-in bot commands.
*   **Security:** Sandboxed execution; only specific host functions (vision, input, delay) are exposed.
*   **Implementation:**
    *   **Parser:** Python `ast` module or `textX` to generate an Abstract Syntax Tree (AST).
    *   **Interpreter:** Custom Python evaluator that walks the AST and executes actions.

### D. User Interface (UI)
*   **Phase 1: Configuration Window (Pre-Launch)**
    *   **Technology:** `Tkinter` or `CustomTkinter`.
    *   **Functionality:** Dynamically generates widgets based on `expose_*` declarations in the script.
        *   `expose_slider("name", min, max)` → Slider
        *   `expose_toggle("name")` → Checkbox
        *   `expose_dropdown("name", ["opt1", "opt2"])` → Dropdown
    *   **Flow:** Load Script → Parse Config → Show GUI → User Confirms → GUI Closes.
*   **Phase 2: Runtime Overlay (In-Game)**
    *   **Technology:** `Dear ImGui` (via `imgui-bundle` Python bindings).
    *   **Features:** Transparent, click-through overlay rendered via DirectX.
    *   **Controls:** Minimalist [Play/Pause], [Restart], [Quit] buttons.
    *   **Footprint:** Negligible performance impact; does not block game input.

### E. Input & Process Management
*   **Input Simulation:** `pydirectinput` or `ctypes` for low-latency keyboard/mouse events.
*   **Process Selection:** User selects target game process by name or PID at launch.

---

## 3. Execution Flow

1.  **Initialization:**
    *   User selects target game process.
    *   User loads `bot_script.txt`.
2.  **Configuration:**
    *   App parses script for `expose_*` variables.
    *   Dynamic Config GUI appears. User adjusts parameters.
    *   User clicks "Confirm". Values are stored in memory.
3.  **Runtime Loop:**
    *   **Capture Thread:** Grabs frames → Queue.
    *   **Vision Threads:** Pull frames → Object/Text Recognition → Result Queue.
    *   **Script Thread:** 
        *   Pulls vision results.
        *   Evaluates DSL script against current state.
        *   Executes actions (Key Press, Delay, Wait).
    *   **Overlay Thread:** Renders ImGui controls.
4.  **State Management:**
    *   States: `RUNNING`, `PAUSED`, `STOPPED`.
    *   **Pause:** Halts script execution; capture continues.
    *   **Restart:** Resets script variables and vision state.
    *   **Quit:** Gracefully shuts down all threads.

---

## 4. Key Requirements

*   **Performance:** >60 FPS capture; optimized vision pipeline for CPU/GPU balance.
*   **Security:** Sandboxed scripting engine; no arbitrary code execution.
*   **Extensibility:** Users can add image samples; scripts define configurable variables.
*   **Documentation:** Comprehensive `bot_script.txt` guide included.
*   **Platform:** Windows 10/11 (64-bit).

---

## 5. Deliverables

1.  **Python Application:** Main executable with integrated modules.
2.  **Scripting Engine:** Parser and interpreter for the custom DSL.
3.  **Vision Module:** Integrated template matching and PaddleOCR/YOLO pipeline.
4.  **UI Modules:** Dynamic config generator and ImGui overlay.
5.  **Documentation:** `bot_script.txt` reference guide and setup instructions.