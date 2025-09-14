# 4robots.md - AI Knowledge Base for Streamlit GB Studio App

## Project Overview
This is a Streamlit application for converting PNG sprites to GB Studio animation format. The app processes sprite images and generates GB Studio-compatible JSON metadata and PNG files.

## Project Structure
```
streamlit_gbstudio_app/
├── algorithms/                    # Core processing modules
│   ├── __init__.py
│   ├── spr_png_to_gbstudio_anim.py      # Main GB Studio animation processor
│   ├── _spr_png_to_gbstudio_anim_o1.py  # Alternative implementation
│   └── spr_rgb_to_3color_layers.py      # RGB to 3-color conversion
├── misc/                         # Utility modules
│   ├── __init__.py
│   ├── arg_parse.py             # Command line argument parsing
│   └── string_lib.py            # String utilities
├── input/test/                   # Test assets
│   ├── assets/sprites/          # Test PNG files
│   └── project/sprites/         # Test GBSRES files
├── app.py                       # Main Streamlit application
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project configuration
└── test_*.py                   # Test files
```

## Key Modules

### 1. `algorithms/spr_png_to_gbstudio_anim.py`
- **Purpose**: Main GB Studio animation processor
- **Key Function**: `process(image, gbsres_data, params)`
- **Features**:
  - Converts PNG sprites to GB Studio format
  - Supports GBSRES template integration
  - Generates JSON metadata for GB Studio
  - Handles different animation states (fixed, multi, multi_movement)
  - Supports tile configuration

### 2. `algorithms/_spr_png_to_gbstudio_anim_o1.py`
- **Purpose**: Alternative GB Studio animation processor
- **Key Function**: `process(image, params)`
- **Features**:
  - Simpler interface (no GBSRES template support)
  - Interleaving functionality for sprite frames
  - JSON structure generation
  - Parameter validation

### 3. `algorithms/spr_rgb_to_3color_layers.py`
- **Purpose**: RGB to 3-color conversion for Game Boy palette
- **Key Function**: `process(image, params="")`
- **Features**:
  - Extracts color triplets from first row
  - Maps RGB colors to Game Boy palette
  - Creates stacked bands for animation layers
  - Handles different image modes (RGB, RGBA)

## Dependencies
- **streamlit>=1.28.0**: Web application framework
- **Pillow>=10.0.0**: Image processing
- **matplotlib>=3.7.0**: Plotting and visualization

## Test Files
- `test_app.py`: Standalone integration test (not unittest-based, runs independently)
- `test_spr_png_to_gbstudio_anim.py`: Comprehensive tests for main processor (9 tests)
- `test_spr_png_to_gbstudio_anim_o1.py`: Tests for alternative processor (7 tests)
- `test_spr_rgb_to_3color_layers.py`: Tests for RGB conversion (24 tests)
- `run_tests.py`: Test runner for all unittest-based suites (excludes test_app.py)

## Virtual Environment Issues
- **PowerShell Execution Policy**: Use `venv\Scripts\activate.bat` instead of `.ps1`
- **Package Installation**: Use `--disable-pip-version-check --no-warn-script-location` flags
- **Silent Installation**: Avoid interactive prompts that cause cancellation
- **Background Installation**: Use `is_background=true` for long-running pip installs
- **Dependency Issues**: Avoid `--no-deps` flag as it breaks streamlit's protobuf dependencies

## Known Issues & Solutions

### 1. Import Errors
- **Issue**: `test_app.py` imported non-existent `spr_png_to_gbstudio_anim_by_ref`
- **Solution**: Changed to `spr_png_to_gbstudio_anim`

### 2. Pixel Art Display Blurring
- **Issue**: Small pixel art images appear blurry when upscaled by browser
- **Solution**: 
  - Use `Image.NEAREST` interpolation for scaling
  - Create temporary files with proper scaling
  - Use HTML with CSS `image-rendering: pixelated` to prevent browser smoothing
  - Base64 encode images for inline display

### 3. Zoom Level Controls
- **Feature**: Added x1, x2, x4, x8, x16, x32 zoom level controls
- **Implementation**:
  - Zoom level selector in sidebar under "Display Settings"
  - Applied to both input and output images and animation GIFs
  - Uses nearest neighbor interpolation for pixel-perfect scaling
  - Visual indicators show current zoom level

### 4. Improved Layout Design
- **Feature**: Redesigned app layout for better user experience
- **Implementation**:
  - Processing controls moved above images for better workflow
  - Input and output images displayed side by side for easy comparison
  - Download button and status messages in dedicated columns
  - GBSRES metadata collapsed by default in expandable section
  - Clear visual hierarchy: Upload → Configure → Process → Compare → Download

### 5. Animation GIF Debug Feature
- **Feature**: Generate animated GIFs for debugging sprite animations
- **Implementation**:
  - Checkbox in "Debug Options" section to enable GIF creation
  - Creates GIFs for each animation state and animation sequence
  - Extracts frames from processed sprite data using tile coordinates
  - Applies proper flips and transformations as defined in GBSRES data
  - Displays GIFs in a grid layout with animation metadata
  - Uses same zoom level as display settings for consistency
  - 5 FPS animation speed (200ms per frame) for smooth debugging
  - Green (0, 255, 0) background shows Game Boy transparent areas
  - Each frame drawn on fresh canvas to prevent accumulation artifacts
  - Pixel-perfect scaling using nearest neighbor interpolation for crisp GIFs
  - Effective zoom level (zoom + 1) for extra clarity and to prevent browser scaling
  - Dual palette system for GIF visualization
  - Auto-extraction: Analyzes input RGB image and extracts dominant colors
  - Custom override: Optional manual palette specification
  - Palette format: background;r1,g1,b1;r2,g2,b2;... (hex colors without #)
  - Background color replaces green (0, 255, 0) transparent areas
  - Palette colors applied to sprite pixels for better visualization
  - Only affects GIF display, not actual GB Studio processing
  - Position-based color extraction from top row (same logic as spr_rgb_to_3color_layers.py)
  - UI shows all 3 colors per palette horizontally (Light, Mid, Dark)
  - Proper GB Studio color mapping: e0f8cf→light, 86c06c→mid, 071821→dark
  - Supports up to 2 palettes (6 colors total) for multi-layer sprites
  - Layer-specific palette mapping: Layer 1 uses first palette, Layer 2 uses second palette
  - 15-bit color quantization option for Game Boy hardware visualization (only shown when GIFs enabled)
  - Button-based state type selection (Fixed, Multi, Multi Movement)
  - Increased GIF scaling to zoom level + 2 for better visibility
  - Color-based palette mapping: Light/mid colors use first palette, dark colors use second palette
  - Simplified layer handling for GIF generation
  - Removed debug output for cleaner console
  - GIF output enabled by default
  - 15-bit quantization enabled by default

### 6. Session State Persistence
- **Feature**: Remember user parameters between sessions
- **Implementation**:
  - All form inputs automatically saved to session state
  - Parameters restored when app reloads or user returns
  - Includes: filename, processing options, tile settings, animation states, zoom level, etc.
  - "Clear All Settings" button to reset to defaults
  - Clears processing results when settings are reset
  - Improves user experience by eliminating need to re-enter settings

### 7. PowerShell Execution Policy
- **Issue**: Cannot run `.ps1` activation scripts
- **Solution**: Use `.bat` files or direct python executable calls

### 8. Package Installation Cancellation
- **Issue**: Interactive prompts cause user cancellation
- **Solution**: Use silent installation flags or background installation

## Test Results
- **Total Tests**: 40 tests across 4 test modules
- **Status**: All tests passing ✅
- **Coverage**: RGB conversion, GB Studio animation, GBSRES integration, app integration
- **Test Modules**:
  - `test_spr_rgb_to_3color_layers.py`: 24 tests (RGB to 3-color conversion)
  - `test_spr_png_to_gbstudio_anim_o1.py`: 7 tests (Alternative GB Studio processor)
  - `test_spr_png_to_gbstudio_anim.py`: 9 tests (Main GB Studio processor with GBSRES)
  - `test_app.py`: Standalone integration test (app functionality)
- **Last Verified**: January 2025 - All tests confirmed passing

## Usage Patterns
1. **Development**: Use `venv\Scripts\python.exe` for direct execution
2. **Testing**: Run `python run_tests.py` for full test suite
3. **App Launch**: Use `streamlit run app.py` (when streamlit is installed)

## File Naming Conventions
- Test files: `test_*.py`
- Algorithm modules: `spr_*` prefix
- Utility modules: Descriptive names in `misc/`

## Configuration Files
- `pyproject.toml`: Project metadata, dependencies, tool configurations
- `requirements.txt`: Minimal runtime dependencies
- `pyvenv.cfg`: Virtual environment configuration

## Windows-Specific Notes
- Use backslashes in paths: `venv\Scripts\python.exe`
- PowerShell has execution policy restrictions
- Use `.bat` files for activation scripts
- Long command lines may cause display issues in PowerShell

## Maintenance Notes
- Keep this file updated when making structural changes
- Document any new modules or significant changes
- Update test coverage information
- Note any environment-specific issues and solutions

## Recent Updates (January 2025)
- **Test Verification**: All 40 tests confirmed passing across 4 test modules
- **Test Runner**: `run_tests.py` provides comprehensive test execution with detailed output
- **Individual Testing**: Each test module can be run independently using unittest
- **Virtual Environment**: Confirmed working with `.\venv\Scripts\python.exe` execution
- **Test Coverage**: Includes app integration testing via `test_app.py` standalone script
- **GIF Debug Feature**: Added animation GIF generation for debugging sprite animations
  - Creates animated GIFs for each animation state and sequence
  - Extracts frames from processed sprite data using tile coordinates
  - Applies proper flips and transformations as defined in GBSRES data
  - Displays in grid layout with animation metadata (state type, frame count, flip info)
  - Uses same zoom level as display settings for consistency
  - 5 FPS animation speed for smooth debugging experience
- **Session State Persistence**: Added parameter memory between sessions
  - All form inputs automatically saved and restored
  - No need to re-enter settings each time
  - "Clear All Settings" button for easy reset
  - Improves user experience significantly

## Layer Palettes Logic (CRITICAL)
- **Layer Palettes Parameter**: Defines GB Studio palette IDs for GBSRES file generation
  - Example: "3,4" means 2 layers using GB Studio palette IDs 3 and 4
  - Number of layers = number of comma-separated values
  - These IDs are used in the generated GBSRES JSON metadata
- **GIF Visualization**: Uses sequential array indices (0, 1, 2...) for extracted palettes
  - Ignore the GB Studio palette IDs for GIF generation
  - Map extracted palettes sequentially: first extracted palette = index 0, second = index 1, etc.
  - GB Studio may have more palettes than what's extracted from the image
- **Key Insight**: Layer palettes define GB Studio palette IDs, not array indices for extracted palettes