import streamlit as st
import zipfile
import io
import os
import tempfile
from PIL import Image
from algorithms.spr_png_to_gbstudio_anim import process, load_gbsres_file
import json


def scale_image_for_display(image, max_width=400, zoom_level=1):
    """Scale an image using nearest neighbor interpolation for pixel art."""
    # Apply zoom level first
    if zoom_level > 1:
        zoomed_width = image.width * zoom_level
        zoomed_height = image.height * zoom_level
        image = image.resize((zoomed_width, zoomed_height), Image.NEAREST)
    
    # Then apply max width constraint if needed
    if image.width <= max_width:
        return image
    
    # Calculate scale factor
    scale_factor = max_width / image.width
    
    # Calculate new dimensions
    new_width = int(image.width * scale_factor)
    new_height = int(image.height * scale_factor)
    
    # Resize using nearest neighbor
    scaled_image = image.resize((new_width, new_height), Image.NEAREST)
    
    return scaled_image


def create_pixel_perfect_display(image, max_width=400, zoom_level=1):
    """Create a pixel-perfect display by scaling and saving to temp file with CSS."""
    # Scale the image using nearest neighbor
    scaled_image = scale_image_for_display(image, max_width, zoom_level)
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    scaled_image.save(temp_file.name, format='PNG')
    temp_file.close()
    
    return temp_file.name, scaled_image.size


def parse_palette_string(palette_str):
    """
    Parse palette string in format: background;r1,g1,b1;r2,g2,b2;...
    
    Args:
        palette_str: String in format "00ff00;ff0000,00ff00,0000ff;0000ff,ffff00,ff00ff"
        
    Returns:
        Dictionary with 'background' and 'palettes' keys
    """
    try:
        parts = palette_str.split(';')
        if len(parts) < 2:
            raise ValueError("Palette must have background and at least one palette")
        
        background = parts[0].strip()
        palettes = []
        
        for i in range(1, len(parts)):
            palette_part = parts[i].strip()
            if palette_part:
                colors = palette_part.split(',')
                if len(colors) != 3:
                    raise ValueError(f"Palette {i} must have exactly 3 colors")
                # Validate hex colors
                for color in colors:
                    color = color.strip()
                    if len(color) != 6 or not all(c in '0123456789abcdefABCDEF' for c in color):
                        raise ValueError(f"Invalid hex color: {color}")
                palettes.append([color.strip().lower() for color in colors])
        
        return {
            'background': background.strip().lower(),
            'palettes': palettes
        }
    except Exception as e:
        raise ValueError(f"Invalid palette format: {e}")


def extract_palette_from_image(image):
    """
    Extract palette colors from an RGB image using the same logic as spr_rgb_to_3color_layers.py.
    
    Extracts color triplets from the first row of the image, following the same pattern:
    - First 3 pixels: first palette
    - 4th pixel: green break (0, 255, 0) 
    - Next 3 pixels: second palette
    - 8th pixel: green break (0, 255, 0)
    - etc.
    
    Args:
        image: PIL Image to extract palette from
        
    Returns:
        Dictionary with 'background' and 'palettes' keys, or None if extraction fails
    """
    try:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        width, height = image.size
        
        if width < 4:
            return None
        
        # Extract color triplets from the first row using the same logic as spr_rgb_to_3color_layers.py
        triplets = _extract_color_triplets_for_palette(image, width)
        
        if not triplets:
            return None
        
        # Convert triplets to hex format
        palettes = []
        for triplet in triplets:
            hex_colors = [f"{r:02x}{g:02x}{b:02x}" for r, g, b in triplet]
            palettes.append(hex_colors)
        
        return {
            'background': '00ff00',  # Keep green as default background
            'palettes': palettes
        }
    except Exception as e:
        warning_msg = f"Warning: Could not extract palette from image: {e}"
        print(warning_msg)  # Keep console output for debugging
        if 'output_log' in st.session_state:
            st.session_state.output_log.append(f"⚠️ {warning_msg}")
        return None


def _extract_color_triplets_for_palette(image: Image.Image, width: int):
    """
    Extract color triplets from the first row of the image.
    This follows the exact same logic as spr_rgb_to_3color_layers.py.
    """
    first_row_pixels = [image.getpixel((x, 0)) for x in range(width)]
    triplets = []
    idx = 0
    
    while idx + 3 < width:
        c1 = first_row_pixels[idx]
        c2 = first_row_pixels[idx + 1]
        c3 = first_row_pixels[idx + 2]
        break_pixel = first_row_pixels[idx + 3]

        # Stop if we hit a green break pixel at the start
        if c1 == (0, 255, 0):
            break

        # Check if this is a valid triplet (followed by green break pixel)
        if break_pixel == (0, 255, 0):
            triplets.append((c1, c2, c3))
            idx += 4  # Move past triplet + break pixel
        else:
            idx += 1  # Move one pixel forward and continue scanning
    
    return triplets


def quantize_to_15bit(image):
    """
    Quantize RGB colors to 15-bit color space for Game Boy visualization.
    
    Args:
        image: PIL Image to quantize
        
    Returns:
        PIL Image with 15-bit quantized colors
    """
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    result = image.copy()
    data = result.getdata()
    new_data = []
    
    for pixel in data:
        r, g, b = pixel
        
        # Convert to 15-bit (5 bits per channel)
        # Scale from 0-255 to 0-31, then back to 0-255
        r_15bit = int((r / 255.0) * 31) * 8  # Scale to 0-248 in steps of 8
        g_15bit = int((g / 255.0) * 31) * 8
        b_15bit = int((b / 255.0) * 31) * 8
        
        # Clamp to valid 15-bit range
        r_15bit = min(248, max(0, r_15bit))
        g_15bit = min(248, max(0, g_15bit))
        b_15bit = min(248, max(0, b_15bit))
        
        new_data.append((r_15bit, g_15bit, b_15bit))
    
    result.putdata(new_data)
    return result




def apply_palette_to_layer(image, palette_colors, palette_array_index=0):
    """
    Apply palette colors to a single layer tile.
    
    Args:
        image: PIL Image tile to apply palette to
        palette_colors: Dictionary with 'background' and 'palettes' keys
        palette_array_index: Index into the extracted palette array (0, 1, 2...)
        
    Returns:
        PIL Image with applied palette
    """
    if not palette_colors or not palette_colors.get('palettes'):
        return image
    
    # Convert to RGB if needed
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Create a copy to modify
    result = image.copy()
    data = result.getdata()
    new_data = []
    
    # GB Studio color mapping
    gb_light = (224, 248, 207)    # e0f8cf
    gb_mid = (134, 192, 108)      # 86c06c  
    gb_dark = (7, 24, 33)         # 071821
    
    # Select the appropriate palette for this layer
    # palette_array_index is the sequential index into the extracted palette array (0, 1, 2, etc.)
    # This is the correct index into the palette_colors['palettes'] array
    
    palette_to_use = None
    if palette_array_index < len(palette_colors['palettes']):
        palette_to_use = palette_colors['palettes'][palette_array_index]
        # Add to debug log if available
        if 'output_log' in st.session_state:
            st.session_state.output_log.append(f"🎨 Using palette array index {palette_array_index}: {', '.join(palette_to_use)}")
    elif len(palette_colors['palettes']) > 0:
        # Fallback to first palette if array index is out of range
        palette_to_use = palette_colors['palettes'][0]
        # Add to debug log if available
        if 'output_log' in st.session_state:
            st.session_state.output_log.append(f"🎨 Palette array index {palette_array_index} out of range, using palette 0: {', '.join(palette_to_use)}")
    
    # Count color mappings for debugging
    color_counts = {'light': 0, 'mid': 0, 'dark': 0, 'other': 0}
    
    for pixel in data:
        r, g, b = pixel
        
        # Check if it's the green background (0, 255, 0)
        if r == 0 and g == 255 and b == 0:
            # Keep green as transparent
            new_data.append(pixel)
        else:
            # Map GB Studio colors to palette colors
            mapped = False
            
            if palette_to_use and len(palette_to_use) >= 3:
                # Check for GB Studio light color (e0f8cf)
                if pixel == gb_light:
                    hex_color = palette_to_use[0]
                    new_r = int(hex_color[0:2], 16)
                    new_g = int(hex_color[2:4], 16)
                    new_b = int(hex_color[4:6], 16)
                    new_data.append((new_r, new_g, new_b))
                    mapped = True
                    color_counts['light'] += 1
                
                # Check for GB Studio mid color (86c06c)
                elif pixel == gb_mid:
                    hex_color = palette_to_use[1]
                    new_r = int(hex_color[0:2], 16)
                    new_g = int(hex_color[2:4], 16)
                    new_b = int(hex_color[4:6], 16)
                    new_data.append((new_r, new_g, new_b))
                    mapped = True
                    color_counts['mid'] += 1
                
                # Check for GB Studio dark color (071821)
                elif pixel == gb_dark:
                    hex_color = palette_to_use[2]
                    new_r = int(hex_color[0:2], 16)
                    new_g = int(hex_color[2:4], 16)
                    new_b = int(hex_color[4:6], 16)
                    new_data.append((new_r, new_g, new_b))
                    mapped = True
                    color_counts['dark'] += 1
            
            if not mapped:
                new_data.append(pixel)  # Keep original if no mapping found
                color_counts['other'] += 1
    
    # Add color mapping debug information to log
    if 'output_log' in st.session_state:
        st.session_state.output_log.append(f"🎨 Palette array index {palette_array_index} color mappings: light={color_counts['light']}, mid={color_counts['mid']}, dark={color_counts['dark']}, other={color_counts['other']}")
    
    result.putdata(new_data)
    return result

def create_animation_gifs(processed_image, zoom_level=1, custom_palette=None, quantize_15bit=False):
    """
    Create animated GIFs from the processed sprite animation data.
    
    Args:
        processed_image: Processed PIL Image with extra_data containing animation metadata
        zoom_level: Zoom level for the GIF frames
        
    Returns:
        Dictionary mapping state names to GIF file paths
    """
    if not hasattr(processed_image, 'extra_data') or not processed_image.extra_data:
        return {}
    
    animation_data = processed_image.extra_data
    if not isinstance(animation_data, dict) or 'states' not in animation_data:
        return {}
    
    gifs = {}
    base_image = processed_image
    
    for state in animation_data['states']:
        state_name = state.get('name', 'unknown')
        state_type = state.get('animationType', 'fixed')
        flip_left = state.get('flipLeft', False)
        
        # Create GIF for each animation in the state
        for anim_index, animation in enumerate(state.get('animations', [])):
            frames = animation.get('frames', [])
            if not frames:
                continue
            
            # Create frame images with proper scaling (zoom level + 2 for extra clarity)
            frame_images = []
            effective_zoom = zoom_level + 2  # Add 2 for extra clarity
            
            for frame in frames:
                # Create a single frame image that combines all layers with proper palette application
                frame_img = create_frame_image(base_image, frame, 1, flip_left, custom_palette)
                if frame_img:
                    # Apply 15-bit quantization if requested
                    if quantize_15bit:
                        frame_img = quantize_to_15bit(frame_img)
                    
                    # Apply effective zoom with nearest neighbor interpolation for pixel-perfect scaling
                    new_width = frame_img.width * effective_zoom
                    new_height = frame_img.height * effective_zoom
                    frame_img = frame_img.resize((new_width, new_height), Image.NEAREST)
                    frame_images.append(frame_img)
            
            if frame_images:
                # Create GIF
                gif_buffer = io.BytesIO()
                frame_images[0].save(
                    gif_buffer,
                    format='GIF',
                    save_all=True,
                    append_images=frame_images[1:],
                    duration=200,  # 200ms per frame (5 FPS)
                    loop=0,  # Infinite loop
                    optimize=True
                )
                gif_buffer.seek(0)
                
                # Save to temporary file
                temp_gif = tempfile.NamedTemporaryFile(delete=False, suffix='.gif')
                temp_gif.write(gif_buffer.getvalue())
                temp_gif.close()
                
                gif_key = f"{state_name}_anim_{anim_index}" if len(state.get('animations', [])) > 1 else state_name
                gifs[gif_key] = {
                    'path': temp_gif.name,
                    'state_type': state_type,
                    'frame_count': len(frame_images),
                    'flip_left': flip_left
                }
    
    return gifs


def create_frame_image(base_image, frame_data, zoom_level=1, flip_left=False, custom_palette=None):
    """
    Create a single frame image from frame data with proper layer composition and palette application.
    
    Args:
        base_image: The processed sprite image
        frame_data: Frame data containing tile information
        zoom_level: Zoom level for the frame (currently unused, scaling done in GIF creation)
        flip_left: Whether to flip the frame horizontally
        custom_palette: Custom palette to apply to layers
        
    Returns:
        PIL Image of the frame or None if no valid tiles
    """
    tiles = frame_data.get('tiles', [])
    if not tiles:
        return None
    
    # Calculate frame dimensions from tile positions
    max_x = max(tile.get('x', 0) + 8 for tile in tiles)  # Assuming 8x16 tiles
    max_y = max(tile.get('y', 0) + 16 for tile in tiles)
    
    # Create a fresh frame canvas with background color
    # This ensures no accumulation between frames
    if custom_palette and custom_palette.get('background'):
        # Use custom background color
        bg_hex = custom_palette['background']
        bg_r = int(bg_hex[0:2], 16)
        bg_g = int(bg_hex[2:4], 16)
        bg_b = int(bg_hex[4:6], 16)
        frame_img = Image.new('RGBA', (max_x, max_y), (bg_r, bg_g, bg_b, 255))
    else:
        # Default green background (Game Boy transparent color)
        frame_img = Image.new('RGBA', (max_x, max_y), (0, 255, 0, 255))
    
    # Group tiles by layer (paletteIndex) and create sequential mapping for GIF visualization
    tiles_by_layer = {}
    palette_index_to_array_index = {}  # Maps converted palette index to sequential array index
    
    for tile in tiles:
        palette_index = tile.get('paletteIndex', 1) - 1  # Convert to 0-based (3->2, 4->3, etc.)
        if palette_index not in tiles_by_layer:
            tiles_by_layer[palette_index] = []
            # Map this palette index to the next sequential palette array index (0, 1, 2...)
            palette_index_to_array_index[palette_index] = len(palette_index_to_array_index)
        tiles_by_layer[palette_index].append(tile)
    
    # Debug: Add layer information to log
    if 'output_log' in st.session_state:
        st.session_state.output_log.append(f"🎬 Found {len(tiles_by_layer)} layers:")
        for layer_idx, layer_tiles in tiles_by_layer.items():
            palette_array_idx = palette_index_to_array_index.get(layer_idx, 0)
            gb_palette_id = layer_idx + 1  # Convert back to GB Studio palette ID
            st.session_state.output_log.append(f"  GB Palette ID {gb_palette_id} (GIF array index {palette_array_idx}): {len(layer_tiles)} tiles")
            if layer_tiles:
                first_tile = layer_tiles[0]
                st.session_state.output_log.append(f"    First tile paletteIndex: {first_tile.get('paletteIndex', 'N/A')}")
                st.session_state.output_log.append(f"    First tile position: ({first_tile.get('x', 0)}, {first_tile.get('y', 0)})")
    
    # Process each layer separately
    for layer_index in sorted(tiles_by_layer.keys()):
        layer_tiles = tiles_by_layer[layer_index]
        
        if 'output_log' in st.session_state:
            st.session_state.output_log.append(f"🎬 Processing layer {layer_index} with {len(layer_tiles)} tiles")
        
        for tile in layer_tiles:
            slice_x = tile.get('sliceX', 0)
            slice_y = tile.get('sliceY', 0)
            tile_x = tile.get('x', 0)
            tile_y = tile.get('y', 0)
            flip_x = tile.get('flipX', False)
            flip_y = tile.get('flipY', False)
            
            # Extract tile from base image
            tile_width = 8  # Default tile width
            tile_height = 16  # Default tile height
            
            try:
                tile_img = base_image.crop((slice_x, slice_y, slice_x + tile_width, slice_y + tile_height))
                
                # Apply flips
                if flip_x:
                    tile_img = tile_img.transpose(Image.FLIP_LEFT_RIGHT)
                if flip_y:
                    tile_img = tile_img.transpose(Image.FLIP_TOP_BOTTOM)
                
                # Apply state-level flip
                if flip_left:
                    tile_img = tile_img.transpose(Image.FLIP_LEFT_RIGHT)
                
                # Apply palette to this layer's tile
                if custom_palette:
                    if 'output_log' in st.session_state:
                        st.session_state.output_log.append(f"🎨 Applying palette to layer {layer_index}, tile at ({tile_x}, {tile_y})")
                    # Map the layer index to the sequential palette array index for GIF visualization
                    palette_array_index = palette_index_to_array_index.get(layer_index, 0)
                    tile_img = apply_palette_to_layer(tile_img, custom_palette, palette_array_index)
                
                # Convert green (0, 255, 0) to transparent for proper layering
                if tile_img.mode == 'RGB':
                    tile_img = tile_img.convert('RGBA')
                
                # Make green pixels transparent
                if tile_img.mode == 'RGBA':
                    data = tile_img.getdata()
                    new_data = []
                    for item in data:
                        # Check if pixel is green (0, 255, 0) and make it transparent
                        if item[0] == 0 and item[1] == 255 and item[2] == 0:
                            new_data.append((0, 0, 0, 0))  # Transparent
                        else:
                            new_data.append(item)
                    tile_img.putdata(new_data)
                
                # Paste tile onto frame with alpha blending
                frame_img.paste(tile_img, (tile_x, tile_y), tile_img)
                
            except Exception as e:
                warning_msg = f"Warning: Could not process tile at ({slice_x}, {slice_y}): {e}"
                print(warning_msg)  # Keep console output for debugging
                if 'output_log' in st.session_state:
                    st.session_state.output_log.append(f"⚠️ {warning_msg}")
                continue
    
    # Note: Zoom level scaling is now handled in the GIF creation function
    # to ensure pixel-perfect scaling for all frames
    return frame_img

def display_pixel_art(image, caption, max_width=400, zoom_level=1):
    """Display pixel art with proper scaling and CSS to prevent blurring."""
    temp_file_path, scaled_size = create_pixel_perfect_display(image, max_width, zoom_level)
    
    # Read the image data as base64
    import base64
    with open(temp_file_path, "rb") as img_file:
        img_data = base64.b64encode(img_file.read()).decode()
    
    # Create HTML with proper image rendering
    html = f"""
    <div style="text-align: center;">
        <img src="data:image/png;base64,{img_data}" 
             style="image-rendering: pixelated; 
                    image-rendering: -moz-crisp-edges; 
                    image-rendering: crisp-edges; 
                    image-rendering: -webkit-optimize-contrast; 
                    image-rendering: optimize-contrast; 
                    image-rendering: -ms-interpolation-mode: nearest-neighbor;
                    max-width: 100%; 
                    height: auto;"
             alt="{caption}">
        <p style="font-size: 0.8em; color: #666; margin-top: 5px;">{caption}</p>
    </div>
    """
    
    # Display the HTML
    st.markdown(html, unsafe_allow_html=True)
    
    # Clean up the temporary file
    try:
        os.unlink(temp_file_path)
    except:
        pass  # Ignore cleanup errors
    
    return scaled_size


def main():
    st.set_page_config(
        page_title="GB Studio Sprite Animator",
        page_icon="🎮",
        layout="wide"
    )
    
    st.title("🎮 GB Studio Sprite Animator")
    st.markdown("Convert PNG sprites to GB Studio animation format")
    
    # Sidebar for parameters
    with st.sidebar:
        st.header("⚙️ Parameters")
        
        # Initialize session state for parameters if not exists
        if 'filename' not in st.session_state:
            st.session_state.filename = "sprite"
        if 'enable_rgb' not in st.session_state:
            st.session_state.enable_rgb = True
        if 'enable_processing' not in st.session_state:
            st.session_state.enable_processing = True
        if 'tile_width' not in st.session_state:
            st.session_state.tile_width = 8
        if 'tile_height' not in st.session_state:
            st.session_state.tile_height = 16
        if 'hor_tiles' not in st.session_state:
            st.session_state.hor_tiles = 1
        if 'vert_tiles' not in st.session_state:
            st.session_state.vert_tiles = 1
        if 'layer_palettes' not in st.session_state:
            st.session_state.layer_palettes = "1"
        if 'zoom_level' not in st.session_state:
            st.session_state.zoom_level = 2
        if 'checksum' not in st.session_state:
            st.session_state.checksum = "TBD"
        if 'create_gifs' not in st.session_state:
            st.session_state.create_gifs = True
        if 'quantize_15bit' not in st.session_state:
            st.session_state.quantize_15bit = True
        
        # Basic parameters
        st.subheader("Basic Settings")
        filename = st.text_input("Filename", value=st.session_state.filename, help="Base name for output files", key="filename_input")
        enable_rgb = st.checkbox("Enable RGB Processing", value=st.session_state.enable_rgb, help="Process RGB color layers", key="enable_rgb_input")
        enable_processing = st.checkbox("Enable Processing", value=st.session_state.enable_processing, help="Generate JSON metadata", key="enable_processing_input")
        
        # Update session state when values change
        st.session_state.filename = filename
        st.session_state.enable_rgb = enable_rgb
        st.session_state.enable_processing = enable_processing
        
        st.subheader("Tile Settings")
        tile_width = st.number_input("Tile Width", min_value=1, max_value=32, value=st.session_state.tile_width, help="Width of each tile in pixels", key="tile_width_input")
        tile_height = st.number_input("Tile Height", min_value=1, max_value=32, value=st.session_state.tile_height, help="Height of each tile in pixels", key="tile_height_input")
        hor_tiles = st.number_input("Horizontal Tiles per Frame", min_value=1, max_value=8, value=st.session_state.hor_tiles, help="Number of tiles horizontally per frame", key="hor_tiles_input")
        vert_tiles = st.number_input("Vertical Tiles per Frame", min_value=1, max_value=8, value=st.session_state.vert_tiles, help="Number of tiles vertically per frame", key="vert_tiles_input")
        
        # Update session state for tile settings
        st.session_state.tile_width = tile_width
        st.session_state.tile_height = tile_height
        st.session_state.hor_tiles = hor_tiles
        st.session_state.vert_tiles = vert_tiles
        
        st.subheader("Animation Settings")
        st.write("Add state types (you can add the same type multiple times):")
        
        # Container for state types - initialize if not exists
        if 'state_types' not in st.session_state:
            st.session_state.state_types = ["fixed"]
        
        # State type buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("➕ Fixed", key="add_fixed"):
                st.session_state.state_types.append("fixed")
                st.rerun()
        with col2:
            if st.button("➕ Multi", key="add_multi"):
                st.session_state.state_types.append("multi")
                st.rerun()
        with col3:
            if st.button("➕ Multi Movement", key="add_multi_movement"):
                st.session_state.state_types.append("multi_movement")
                st.rerun()
        
        # Display current state types
        if st.session_state.state_types:
            st.write("Current state types:")
            for i, state in enumerate(st.session_state.state_types):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{i+1}. {state}")
                with col2:
                    if st.button("🗑️", key=f"remove_{i}"):
                        st.session_state.state_types.pop(i)
                        st.rerun()
        
        state_types = st.session_state.state_types
        
        st.subheader("Layer Settings")
        layer_palettes = st.text_input("Layer Palettes", value=st.session_state.layer_palettes, help="Comma-separated palette indices (e.g., '1,2,3')", key="layer_palettes_input")
        
        # Update session state for layer settings
        st.session_state.layer_palettes = layer_palettes
        
        st.subheader("Display Settings")
        zoom_level = st.selectbox(
            "Zoom Level",
            options=[1, 2, 4, 8, 16, 32],
            index=[1, 2, 4, 8, 16, 32].index(st.session_state.zoom_level) if st.session_state.zoom_level in [1, 2, 4, 8, 16, 32] else 1,
            format_func=lambda x: f"x{x}",
            help="Zoom level for displaying images",
            key="zoom_level_input"
        )
        
        # Update session state for zoom level
        st.session_state.zoom_level = zoom_level
        
        st.subheader("Advanced")
        checksum = st.text_input("Checksum", value=st.session_state.checksum, help="File checksum (leave as TBD for auto)", key="checksum_input")
        
        # Update session state for checksum
        st.session_state.checksum = checksum
        
        st.subheader("Debug Options")
        create_gifs = st.checkbox("Create GIFs", value=st.session_state.create_gifs, help="Generate animated GIFs for debugging animations", key="create_gifs_input")
        
        # Update session state for create_gifs
        st.session_state.create_gifs = create_gifs
        
        # Show 15-bit mode only if GIFs are enabled
        if create_gifs:
            quantize_15bit = st.checkbox("15-bit Color Quantization", value=st.session_state.get('quantize_15bit', True), help="Quantize colors to 15-bit for Game Boy hardware visualization", key="quantize_15bit_input")
            st.session_state.quantize_15bit = quantize_15bit
        
        # Palette settings for GIF visualization
        if create_gifs:
            st.subheader("GIF Visualization Palette")
            
            # Show extracted palette if available
            if 'extracted_palette' in st.session_state and st.session_state.extracted_palette:
                st.write("**Auto-Extracted Palette from Image:**")
                extracted = st.session_state.extracted_palette
                bg_hex = extracted['background']
                st.write(f"Background: `#{bg_hex}`")
                
                for i, palette in enumerate(extracted['palettes']):
                    st.write(f"**Extracted {i+1}:** `{', '.join(palette)}`")
                    
                    # Show all 3 colors horizontally
                    if len(palette) >= 3:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.color_picker(f"Light", value=f"#{palette[0]}", disabled=True, key=f"extracted_{i}_0")
                        with col2:
                            st.color_picker(f"Mid", value=f"#{palette[1]}", disabled=True, key=f"extracted_{i}_1")
                        with col3:
                            st.color_picker(f"Dark", value=f"#{palette[2]}", disabled=True, key=f"extracted_{i}_2")
            
            # Custom palette override
            st.write("**Custom Palette Override (optional):**")
            palette_input = st.text_input(
                "Custom Palette", 
                value=st.session_state.get('gif_palette', ''),
                help="Format: background;r1,g1,b1;r2,g2,b2;... (hex colors without #). Leave empty to use auto-extracted palette.",
                key="gif_palette_input"
            )
            st.session_state.gif_palette = palette_input
            
            # Show custom palette preview
            if palette_input:
                try:
                    palette_colors = parse_palette_string(palette_input)
                    if palette_colors:
                        st.write("**Custom Palette Preview:**")
                        
                        # Show background
                        st.write(f"Background: `#{palette_colors['background']}`")
                        col_bg = st.columns(1)
                        with col_bg[0]:
                            st.color_picker("Background", value=f"#{palette_colors['background']}", disabled=True, key="custom_bg")
                        
                        # Show each palette with all 3 colors
                        for i, palette in enumerate(palette_colors['palettes']):
                            st.write(f"**Custom {i+1}:** `{', '.join(palette)}`")
                            
                            # Show all 3 colors horizontally
                            if len(palette) >= 3:
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.color_picker(f"Light", value=f"#{palette[0]}", disabled=True, key=f"custom_{i}_0")
                                with col2:
                                    st.color_picker(f"Mid", value=f"#{palette[1]}", disabled=True, key=f"custom_{i}_1")
                                with col3:
                                    st.color_picker(f"Dark", value=f"#{palette[2]}", disabled=True, key=f"custom_{i}_2")
                except Exception as e:
                    st.error(f"Invalid palette format: {e}")
                    st.session_state.gif_palette = ''  # Reset to empty
        
        # Clear settings button
        st.subheader("Session Management")
        if st.button("🗑️ Clear All Settings", help="Reset all parameters to default values"):
            # Clear all session state parameters
            st.session_state.filename = "sprite"
            st.session_state.enable_rgb = True
            st.session_state.enable_processing = True
            st.session_state.tile_width = 8
            st.session_state.tile_height = 16
            st.session_state.hor_tiles = 1
            st.session_state.vert_tiles = 1
            st.session_state.layer_palettes = "1"
            st.session_state.zoom_level = 2
            st.session_state.checksum = "TBD"
            st.session_state.create_gifs = True
            st.session_state.quantize_15bit = True
            st.session_state.gif_palette = ""
            st.session_state.extracted_palette = None
            st.session_state.state_types = ["fixed"]
            # Clear processing results
            if 'processed_image' in st.session_state:
                del st.session_state.processed_image
            if 'zip_buffer' in st.session_state:
                del st.session_state.zip_buffer
            if 'animation_gifs' in st.session_state:
                del st.session_state.animation_gifs
            if 'processing_success' in st.session_state:
                del st.session_state.processing_success
            if 'output_log' in st.session_state:
                del st.session_state.output_log
            st.rerun()
    
    # Main content area
    st.header("📁 Upload & Process Sprite")
    
    # File upload section
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🖼️ PNG Sprite")
        uploaded_png = st.file_uploader(
            "Choose a PNG file",
            type=['png'],
            help="Upload a PNG sprite image to process",
            key="png_uploader"
        )
    
    with col2:
        st.subheader("📄 GBSRES Template")
        uploaded_gbsres = st.file_uploader(
            "Choose a GBSRES file (optional)",
            type=['gbsres'],
            help="Upload a GBSRES file to use as template (preserves ID and metadata)",
            key="gbsres_uploader"
        )
    
    if uploaded_png is not None:
        # Display the uploaded image
        image = Image.open(uploaded_png)
        
        # Load GBSRES data if provided
        gbsres_data = None
        if uploaded_gbsres is not None:
            gbsres_data = load_gbsres_file(uploaded_gbsres)
            if gbsres_data:
                st.success("✅ GBSRES template loaded successfully!")
            else:
                st.warning("⚠️ Could not load GBSRES file. Processing without template.")
        
        # Processing controls and results above images
        st.subheader("🔧 Processing & Results")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.button("🚀 Process Sprite", type="primary", use_container_width=True):
                with st.spinner("Processing sprite..."):
                    try:
                        # Clear output log at start of processing
                        st.session_state.output_log = []
                        st.session_state.output_log.append(f"🚀 Starting sprite processing for '{filename}'")
                        st.session_state.output_log.append(f"📊 Parameters: RGB={enable_rgb}, Processing={enable_processing}")
                        st.session_state.output_log.append(f"🔧 Tile settings: {tile_width}x{tile_height}, {hor_tiles}x{vert_tiles} tiles per frame")
                        st.session_state.output_log.append(f"🎬 State types: {', '.join(state_types)}")
                        st.session_state.output_log.append(f"🎨 Layer palettes: {layer_palettes}")
                        
                        # Prepare parameters
                        params = f"fname={filename} processing={enable_processing} rgb={'y' if enable_rgb else 'n'} twidth={tile_width} theight={tile_height} htiles={hor_tiles} vtiles={vert_tiles} states={','.join(state_types)} palettes={layer_palettes} chksum={checksum}"
                        
                        # Process the image with optional GBSRES template
                        processed_image = process(image, gbsres_data, params)
                        
                        # Add processing completion to log
                        st.session_state.output_log.append("✅ Sprite processing completed successfully")
                        
                        # Store processed image in session state
                        st.session_state.processed_image = processed_image
                        st.session_state.zip_buffer = create_zip_file(processed_image, filename, enable_rgb)
                        st.session_state.processing_success = True
                        
                        # Extract palette from input image for GIF visualization and layer processing
                        st.session_state.output_log.append("🎨 Extracting palette from input image...")
                        extracted_palette = extract_palette_from_image(image)
                        st.session_state.extracted_palette = extracted_palette
                        
                        # Log extracted palette information
                        if extracted_palette:
                            st.session_state.output_log.append(f"📋 Auto-extracted background: #{extracted_palette['background']}")
                            st.session_state.output_log.append(f"📋 Found {len(extracted_palette['palettes'])} palettes in image")
                            for i, palette in enumerate(extracted_palette['palettes']):
                                st.session_state.output_log.append(f"📋 Auto-extracted palette {i+1}: {', '.join(palette)}")
                            
                            # Log layer configuration
                            layer_count = len(layer_palettes.split(','))
                            st.session_state.output_log.append(f"🎨 Configured for {layer_count} layers: {layer_palettes}")
                            
                            # Map palette indices to array indices
                            palette_indices = [int(x.strip()) for x in layer_palettes.split(',')]
                            st.session_state.output_log.append(f"🎨 Palette indices: {palette_indices}")
                            
                            # Check if palette indices are valid
                            max_palette_index = max(palette_indices) if palette_indices else 0
                            if max_palette_index > len(extracted_palette['palettes']):
                                st.session_state.output_log.append(f"⚠️ Warning: Palette index {max_palette_index} exceeds available palettes ({len(extracted_palette['palettes'])})")
                                st.session_state.output_log.append("💡 Some layers will fall back to available palettes")
                        else:
                            st.session_state.output_log.append("⚠️ Could not extract palette from image")
                        
                        # Create GIFs if enabled
                        if create_gifs:
                            
                            # Determine which palette to use
                            palette_to_use = None
                            if 'gif_palette' in st.session_state and st.session_state.gif_palette:
                                st.session_state.output_log.append("🎨 Using custom palette override...")
                                # Use custom palette if provided
                                try:
                                    palette_to_use = parse_palette_string(st.session_state.gif_palette)
                                    st.session_state.output_log.append(f"📋 Custom background: #{palette_to_use['background']}")
                                    for i, palette in enumerate(palette_to_use['palettes']):
                                        st.session_state.output_log.append(f"📋 Custom palette {i+1}: {', '.join(palette)}")
                                except Exception as e:
                                    st.warning(f"Invalid custom palette format: {e}. Using auto-extracted palette.")
                                    st.session_state.output_log.append(f"⚠️ Invalid custom palette: {e}, falling back to auto-extracted")
                                    palette_to_use = extracted_palette
                            else:
                                st.session_state.output_log.append("🎨 Using auto-extracted palette")
                                # Use auto-extracted palette
                                palette_to_use = extracted_palette
                            
                            st.session_state.output_log.append("🎬 Creating animation GIFs...")
                            st.session_state.animation_gifs = create_animation_gifs(processed_image, zoom_level, palette_to_use, st.session_state.get('quantize_15bit', False))
                            
                            # Log GIF creation results
                            if st.session_state.animation_gifs:
                                st.session_state.output_log.append(f"✅ Created {len(st.session_state.animation_gifs)} animation GIFs")
                                for gif_name, gif_info in st.session_state.animation_gifs.items():
                                    st.session_state.output_log.append(f"  🎬 {gif_name}: {gif_info['frame_count']} frames, type={gif_info['state_type']}")
                            else:
                                st.session_state.output_log.append("⚠️ No animations found to create GIFs from")
                        else:
                            st.session_state.output_log.append("🎬 GIF creation disabled")
                            st.session_state.animation_gifs = {}
                            st.session_state.extracted_palette = None
                        
                        st.rerun()  # Refresh to show the processed image
                        
                    except Exception as e:
                        st.error(f"❌ Error processing image: {str(e)}")
                        st.session_state.output_log.append(f"❌ ERROR: {str(e)}")
                        st.session_state.processing_success = False
        
        with col2:
            if 'processed_image' in st.session_state and st.session_state.get('processing_success', False):
                st.success("✅ Processing completed!")
        
        with col3:
            if 'zip_buffer' in st.session_state and st.session_state.get('processing_success', False):
                st.download_button(
                    label="📦 Download ZIP",
                    data=st.session_state.zip_buffer.getvalue(),
                    file_name=f"{filename}_gbstudio.zip",
                    mime="application/zip",
                    use_container_width=True
                )
        
        # Images side by side
        st.subheader("🖼️ Image Comparison")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**📤 Input Image**")
            scaled_size = display_pixel_art(image, f"Original Image (x{zoom_level})", zoom_level=zoom_level)
            st.info(f"Original size: {image.size[0]}x{image.size[1]} pixels | Display zoom: x{zoom_level}")
        
        with col2:
            st.markdown("**📤 Output Image**")
            if 'processed_image' in st.session_state:
                processed_image = st.session_state.processed_image
                scaled_size = display_pixel_art(processed_image, f"Processed Sprite (x{zoom_level})", zoom_level=zoom_level)
                st.info(f"Processed size: {processed_image.size[0]}x{processed_image.size[1]} pixels | Display zoom: x{zoom_level}")
            else:
                st.info("👆 Click 'Process Sprite' to see the output image here")
        
        # Animation GIFs display
        if 'animation_gifs' in st.session_state and st.session_state.animation_gifs:
            st.subheader("🎬 Animation GIFs")
            st.markdown("**Debug animations by viewing the generated GIFs:**")
            
            gifs = st.session_state.animation_gifs
            if gifs:
                # Display GIFs in a grid
                cols = st.columns(min(len(gifs), 3))  # Max 3 columns
                
                for i, (gif_name, gif_info) in enumerate(gifs.items()):
                    with cols[i % 3]:
                        st.markdown(f"**{gif_name}**")
                        st.markdown(f"*Type: {gif_info['state_type']}*")
                        st.markdown(f"*Frames: {gif_info['frame_count']}*")
                        if gif_info['flip_left']:
                            st.markdown("*Flipped Left*")
                        
                        # Display the GIF at its native size to prevent browser scaling
                        try:
                            with open(gif_info['path'], 'rb') as gif_file:
                                gif_data = gif_file.read()
                                # Display at native size to prevent browser upscaling
                                st.image(gif_data, width=None, use_container_width=False)
                        except Exception as e:
                            st.error(f"Could not display GIF: {e}")
            else:
                st.info("No animations found to create GIFs from.")
        
        # GBSRES metadata display (collapsed by default)
        if 'processed_image' in st.session_state and st.session_state.get('processing_success', False):
            processed_image = st.session_state.processed_image
            
            with st.expander("📄 Generated GBSRES Metadata", expanded=False):
                if hasattr(processed_image, 'extra_data') and processed_image.extra_data:
                    if isinstance(processed_image.extra_data, str):
                        st.info(f"Processing info: {processed_image.extra_data}")
                    else:
                        st.json(processed_image.extra_data)
        
        # Processing output log (read-only debug section)
        if 'processed_image' in st.session_state and st.session_state.get('processing_success', False):
            st.subheader("📋 Processing Output Log")
            
            # Initialize session state for output log if not exists
            if 'output_log' not in st.session_state:
                st.session_state.output_log = []
            
            # Display the output log in a read-only text area
            log_content = "\n".join(st.session_state.output_log) if st.session_state.output_log else "No processing output yet..."
            
            st.text_area(
                "Debug Output",
                value=log_content,
                height=200,
                disabled=True,
                help="Shows processing debug information including layer palette details"
            )
            
            # Clear log button
            if st.button("🗑️ Clear Log", help="Clear the processing output log"):
                st.session_state.output_log = []
                st.rerun()
    
    else:
        st.info("👆 Please upload a PNG file to begin processing")
    
    # Instructions
    with st.expander("📖 Instructions"):
        st.markdown("""
        ### How to use this tool:
        
        1. **Upload a PNG file** - Your sprite image (required)
        2. **Upload a GBSRES file** - Template file to preserve ID and metadata (optional)
        3. **Configure parameters** in the sidebar:
           - **Basic Settings**: Set filename and processing options
           - **Tile Settings**: Define tile dimensions and frame layout
           - **Animation Settings**: Add multiple state types (same type can be added multiple times)
           - **Layer Settings**: Set palette indices for layers
           - **Debug Options**: Enable GIF creation for animation debugging
        4. **Click Process Sprite** to generate the GB Studio files
        5. **View Animation GIFs** (if enabled) to debug your animations
        6. **Download the ZIP file** containing:
           - `/assets/sprites/` - Processed PNG file
           - `/project/sprites/` - GB Studio resource file (.gbsres)
        
        ### File Uploads:
        
        - **PNG File**: Your sprite image to process (required)
        - **GBSRES File**: Template file to use as starting point (optional)
          - Preserves important metadata like ID, name, symbol
          - If not provided, generates new metadata
          - Useful for maintaining consistency across sprite variations
        
        ### Parameter Explanations:
        
        - **Tile Width/Height**: Size of individual tiles in pixels
        - **Tiles per Frame**: How many tiles make up one animation frame
        - **State Types**: Different animation patterns (fixed, multi, etc.) - you can add the same type multiple times
        - **Layer Palettes**: Color palette indices for different layers
        - **RGB Processing**: Converts RGB images to 3-color GB Studio format (enabled by default)
        
        ### Debug Features:
        
        - **Processing Output Log**: Real-time debug information display
          - Shows processing parameters and layer palette information
          - Displays auto-extracted and custom palette details
          - Logs GIF creation results and animation metadata
          - Read-only text area with clear log functionality
          - Temporary debug feature for development and troubleshooting
        
        - **Create GIFs**: Generates animated GIFs for each animation state
          - Shows how your sprite will animate in GB Studio
          - Helps debug animation timing and frame sequences
          - Displays state type, frame count, and flip information
          - GIFs are created with the same zoom level as your display settings
          - **Dual Palette System**: Auto-extraction + custom override
            - **Auto-Extracted Palette**: Automatically extracted from input RGB image
              - Analyzes image colors and groups them into palettes
              - Shows the most common colors from your sprite
              - Displays color preview and hex values
            - **Custom Palette Override**: Optional manual palette specification
              - Format: `background;r1,g1,b1;r2,g2,b2;...` (hex colors without #)
              - Example: `00ff00;ff0000,00ff00,0000ff;0000ff,ffff00,ff00ff`
              - Overrides auto-extracted palette when provided
              - Leave empty to use auto-extracted palette
            - Background color replaces green (0, 255, 0) areas
            - Palette colors are applied to sprite pixels
            - Only affects GIF visualization, not the actual GB Studio output
        
        ### Session Management:
        
        - **Parameter Persistence**: All settings are automatically saved and restored between sessions
          - No need to re-enter parameters each time you use the app
          - Settings persist until you clear them or close the browser
        - **Clear Settings**: Use the "Clear All Settings" button to reset to defaults
          - Resets all parameters to their initial values
          - Clears any processed results and generated GIFs
        """)


def create_zip_file(processed_image, filename, enable_rgb):
    """Create a ZIP file with the proper folder structure."""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the processed PNG to assets/sprites/
        png_buffer = io.BytesIO()
        processed_image.save(png_buffer, format='PNG')
        png_buffer.seek(0)
        zip_file.writestr(f"assets/sprites/{filename}.png", png_buffer.getvalue())
        
        # Add the JSON metadata to project/sprites/
        if hasattr(processed_image, 'extra_data') and processed_image.extra_data:
            if isinstance(processed_image.extra_data, dict):
                json_buffer = io.BytesIO()
                json_str = json.dumps(processed_image.extra_data, indent=2)
                json_buffer.write(json_str.encode('utf-8'))
                json_buffer.seek(0)
                zip_file.writestr(f"project/sprites/{filename}.gbsres", json_buffer.getvalue())
    
    zip_buffer.seek(0)
    return zip_buffer


if __name__ == "__main__":
    main()
