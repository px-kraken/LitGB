# GB Studio Sprite Animator

A Streamlit web application for converting PNG sprites to GB Studio animation format.

## Features

- Upload PNG sprite images
- Configure tile dimensions and animation settings
- Process RGB images to 3-color GB Studio format
- Generate GB Studio resource files (.gbsres)
- Download processed files as a ZIP archive
- **Pixel-perfect image display** with nearest neighbor scaling
- **Before/after image comparison** showing original and processed sprites

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run app.py
```

## Usage

1. Open the web application in your browser
2. Upload a PNG sprite image
3. Configure parameters in the sidebar:
   - **Basic Settings**: Filename and processing options
   - **Tile Settings**: Tile dimensions and frame layout
   - **Animation Settings**: Add multiple state types (same type can be added multiple times)
   - **Layer Settings**: Palette indices for layers
4. Click "Process Sprite" to generate GB Studio files
5. Download the ZIP file containing:
   - `/assets/sprites/` - Processed PNG file
   - `/project/sprites/` - GB Studio resource file (.gbsres)

## Parameters

- **Tile Width/Height**: Size of individual tiles in pixels
- **Tiles per Frame**: How many tiles make up one animation frame
- **State Types**: Different animation patterns (fixed, multi, etc.) - you can add the same type multiple times
- **Layer Palettes**: Color palette indices for different layers
- **RGB Processing**: Converts RGB images to 3-color GB Studio format (enabled by default)

## File Structure

```
streamlit_gbstudio_app/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── README.md                      # This file
├── algorithms/                     # Processing algorithms
│   ├── __init__.py
│   ├── spr_png_to_gbstudio_anim_by_ref.py
│   ├── _spr_png_to_gbstudio_anim_o1.py
│   └── spr_rgb_to_3color_layers.py
└── misc/                          # Utility modules
    ├── __init__.py
    ├── arg_parse.py
    └── string_lib.py
```
