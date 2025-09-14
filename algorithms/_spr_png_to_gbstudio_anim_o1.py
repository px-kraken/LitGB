import uuid
from typing import List, Dict, Any, Tuple

from PIL import Image

from misc.arg_parse import argdict, auto_cast

import matplotlib.pyplot as plt


def show(image: Image.Image) -> None:
    """Display an image using matplotlib."""
    plt.imshow(image)
    plt.show()


def _is_empty(image: Image.Image, left: int, upper: int, right: int, lower: int) -> bool:
    """Check if a region of the image is empty (all green pixels)."""
    if left >= right or upper >= lower:
        return True
    try:
        cropped = image.crop((left, upper, right, lower))
        return all(px == (0, 255, 0) for px in cropped.getdata())
    except (ValueError, OSError):
        return True


def interleave(image: Image.Image, tile_height: int, vert_tiles_per_frame: int) -> Image.Image:
    """
    Interleave image rows from AAAABBBB pattern to ABABABAB pattern.

    This function processes an image by dividing it into horizontal rows of specified
    height, splitting into two sections (A and B) with equal number of rows, then interleaving them.

    Parameters:
    -----------
    image : Image.Image
        The input PIL Image object to be processed
    tile_height : int
        Height of individual tiles in pixels
    vert_tiles_per_frame : int
        Number of vertical tiles per frame/row group

    Returns:
    --------
    Image.Image
        A new PIL Image with rows interleaved in ABAB pattern

    Example:
    --------
    Original row order: [A0, A1, A2, A3, B0, B1, B2, B3] (n=4)
    After processing:   [A0, B0, A1, B1, A2, B2, A3, B3]

    Where each 'A' and 'B' represents a row group of height:
    tile_height * vert_tiles_per_frame

    Notes:
    ------
    - The image height should be divisible by (tile_height * vert_tiles_per_frame * 2)
      for optimal results
    - Any partial rows at the bottom of the image will be discarded
    """
    if not isinstance(image, Image.Image):
        raise TypeError("image must be a PIL Image object")
    
    if tile_height <= 0 or vert_tiles_per_frame <= 0:
        raise ValueError("tile_height and vert_tiles_per_frame must be positive")

    # Calculate the height of each row to process
    row_height = tile_height * vert_tiles_per_frame

    # Get image dimensions
    width, height = image.size
    
    if height < row_height * 2:
        # Not enough rows to interleave, return original image
        return image.copy()

    # Calculate total number of complete rows
    total_rows = height // row_height

    # For AAAABBBB pattern, we need an even number of total rows to split into two equal groups
    if total_rows % 2 != 0:
        total_rows -= 1  # Discard last row if odd number

    if total_rows < 2:
        # Not enough rows to interleave, return original image
        return image.copy()

    # Calculate n - number of rows in each group (A and B)
    n = total_rows // 2

    # Split rows into A section (first n rows) and B section (next n rows)
    a_rows = []
    b_rows = []

    # Extract A rows (first n rows)
    for i in range(n):
        y_start = i * row_height
        y_end = y_start + row_height
        row = image.crop((0, y_start, width, y_end))
        a_rows.append(row)

    # Extract B rows (next n rows)
    for i in range(n, total_rows):
        y_start = i * row_height
        y_end = y_start + row_height
        row = image.crop((0, y_start, width, y_end))
        b_rows.append(row)

    # Create a new image for the result
    result = Image.new('RGB', (width, height))

    # Interleave the rows: A0, B0, A1, B1, A2, B2, ..., A(n-1), B(n-1)
    result_y = 0
    for i in range(n):
        # Paste A row
        result.paste(a_rows[i], (0, result_y))
        result_y += row_height

        # Paste B row
        result.paste(b_rows[i], (0, result_y))
        result_y += row_height

    return result


def process(image: Image.Image, params: str = "") -> Image.Image:
    """
    Process an image for GB Studio animation generation.
    
    Processes the given image, slicing it into frames based on configurable tile patches,
    and generates a JSON structure for GB Studio. Each frame consists of tiles stacked
    vertically and horizontally as specified.

    Args:
        image: PIL Image to process
        params: Parameter string for configuration
        
    Returns:
        Processed PIL Image with extra_data containing JSON metadata
    """
    if not isinstance(image, Image.Image):
        raise TypeError("image must be a PIL Image object")

    # Basic configuration
    img_width, img_height = image.size
    args = argdict(params)

    # Parse parameters with defaults
    fname = args.setdefault('fname', 'TBD')
    name = fname.split('\\')[-1][:-4] if fname != 'TBD' else 'unnamed_sprite'
    checksum = args.setdefault('chksum', 'TBD')
    tile_width = args.setdefault('twidth', 8)
    tile_height = args.setdefault('theight', 16)
    state_types = list((auto_cast(a.strip()) for a in str(args.setdefault('states', "fixed")).split(",")))
    hor_tiles_per_frame = args.setdefault('htiles', 1)
    vert_tiles_per_frame = args.setdefault('vtiles', 1)
    layer_palettes = list((auto_cast(a.strip()) for a in str(args.setdefault('palettes', "1")).split(",")))
    layer_count = len(layer_palettes)

    # Validate parameters
    if tile_width <= 0 or tile_height <= 0:
        raise ValueError("Tile dimensions must be positive")
    if hor_tiles_per_frame <= 0 or vert_tiles_per_frame <= 0:
        raise ValueError("Tiles per frame must be positive")
    if not layer_palettes or any(str(p).strip() == "" for p in layer_palettes):
        raise ValueError("At least one layer palette must be specified")

    # Debug output
    print(f"Processing sprite: {name}")
    print(f"Tile size: {tile_width}x{tile_height}")
    print(f"Frame size: {hor_tiles_per_frame}x{vert_tiles_per_frame} tiles")
    print(f"States: {state_types}")
    print(f"Layers: {layer_count}")

    # Calculate horizontal compensation
    h_compensation = 0 if hor_tiles_per_frame <= 2 else (hor_tiles_per_frame - 2) * -4

    # Interleave the image
    image = interleave(image, tile_height, vert_tiles_per_frame)

    # Calculate maximum frames
    max_frames = img_width // (hor_tiles_per_frame * tile_width)
    if max_frames <= 0:
        raise ValueError("Image width is too small for the specified tile configuration")

    # Generate the JSON structure
    data = _create_base_json_structure(name, checksum, img_width, img_height, 
                                     hor_tiles_per_frame, vert_tiles_per_frame, tile_width, tile_height)

    # Process each state
    state_offset = 0
    for state_index, state_type in enumerate(state_types):
        anim_count = _get_animation_count(state_type)
        flip_left = '#f' in state_type
        clean_state_type = state_type.replace('#f', "")

        state = _create_state(state_index, clean_state_type, flip_left)
        
        # Process each animation in the state
        for animation_index in range(anim_count):
            animation = _create_animation()
            
            # Process frames for this animation
            for frame_index in range(max_frames):
                data['numFrames'] += 1
                frame = _create_frame()
                
                # Process tiles for this frame
                tiles = _create_frame_tiles(image, frame_index, state_offset, animation_index,
                                          vert_tiles_per_frame, hor_tiles_per_frame, layer_count,
                                          tile_width, tile_height, h_compensation, layer_palettes,
                                          data['numTiles'], state_index)
                
                frame["tiles"] = tiles
                
                # Check if frame is empty and break if so
                if all(_is_empty(image, tile["sliceX"], tile["sliceY"], 
                               tile["sliceX"] + tile_width, tile["sliceY"] + tile_height) 
                       for tile in frame["tiles"]):
                    break
                else:
                    data['numTiles'] += len(tiles)
                    animation["frames"].append(frame)

            state["animations"].append(animation)
        
        data["states"].append(state)
        state_offset += vert_tiles_per_frame * layer_count * anim_count

    image.extra_data = data
    return image


def _create_base_json_structure(name: str, checksum: str, img_width: int, img_height: int,
                               hor_tiles_per_frame: int, vert_tiles_per_frame: int,
                               tile_width: int, tile_height: int) -> Dict[str, Any]:
    """Create the base JSON structure for the sprite."""
    return {
        "_resourceType": "sprite",
        "id": str(uuid.uuid4()),
        "name": name,
        "symbol": "sprite_" + name.replace(" ", "_"),
        "numFrames": 0,
        "filename": name + ".png",
        "checksum": checksum,
        "width": img_width,
        "height": img_height,
        "states": [],
        "numTiles": 0,
        "canvasWidth": hor_tiles_per_frame * tile_width,
        "canvasHeight": vert_tiles_per_frame * tile_height,
        "boundsX": 0,
        "boundsY": 0,
        "boundsWidth": hor_tiles_per_frame * tile_width,
        "boundsHeight": vert_tiles_per_frame * tile_height,
        "animSpeed": 15
    }


def _get_animation_count(state_type: str) -> int:
    """Get the number of animations for a given state type."""
    animation_counts = {
        'fixed': 1, 
        'multi#f': 3, 
        'multi': 4, 
        'multi_movement#f': 6, 
        'multi_movement': 8
    }
    return animation_counts.get(state_type, 1)


def _create_state(state_index: int, state_type: str, flip_left: bool) -> Dict[str, Any]:
    """Create a state dictionary."""
    return {
        "id": str(uuid.uuid4()),
        "name": f"state_{state_index}",
        "animationType": state_type,
        "flipLeft": flip_left,
        "animations": []
    }


def _create_animation() -> Dict[str, Any]:
    """Create an animation dictionary."""
    return {
        "id": str(uuid.uuid4()),
        "frames": []
    }


def _create_frame() -> Dict[str, Any]:
    """Create a frame dictionary."""
    return {
        "id": str(uuid.uuid4()),
        "tiles": []
    }


def _create_frame_tiles(image: Image.Image, frame_index: int, state_offset: int, animation_index: int,
                       vert_tiles_per_frame: int, hor_tiles_per_frame: int, layer_count: int,
                       tile_width: int, tile_height: int, h_compensation: int, layer_palettes: List[int],
                       num_tiles: int, state_index: int) -> List[Dict[str, Any]]:
    """Create tiles for a frame."""
    tiles = []
    tile_in_frame = 0
    
    for v_tile_index in range(vert_tiles_per_frame):
        for h_tile_index in range(hor_tiles_per_frame):
            for layer_index in range(layer_count):
                h_px_index = (h_tile_index + frame_index * hor_tiles_per_frame) * tile_width
                v_px_index = (state_offset + 
                             vert_tiles_per_frame * layer_count * animation_index +
                             vert_tiles_per_frame * layer_index +
                             v_tile_index) * tile_height

                tile = {
                    "_comment": f"item: {num_tiles}   state: {state_index}   anim: {animation_index}   frame: {frame_index}   tile {tile_in_frame}   layer: {layer_index}",
                    "id": str(uuid.uuid4()),
                    "x": h_tile_index * tile_width + h_compensation,
                    "y": v_tile_index * tile_height,
                    "sliceX": h_px_index,
                    "sliceY": v_px_index,
                    "palette": 0,
                    "flipX": False,
                    "flipY": False,
                    "objPalette": "OBP0",
                    "paletteIndex": layer_palettes[layer_index],
                    "priority": False
                }
                
                tiles.append(tile)
                tile_in_frame += 1
    
    return tiles
