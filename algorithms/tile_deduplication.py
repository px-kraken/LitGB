from typing import Dict, List, Tuple, Any
from PIL import Image
import hashlib


def process(image: Image.Image, params: str = "") -> Image.Image:
    """
    Deduplicate tiles in a processed sprite by replacing duplicate tiles with references to the first occurrence.
    
    This function analyzes all tiles across layers, frames, and animations to find exact duplicates
    and replaces them with references to the first occurrence, helping save memory.
    
    Args:
        image: PIL Image that has been processed by spr_png_to_gbstudio_anim
        params: Parameter string (unused in this implementation)
        
    Returns:
        PIL Image with deduplicated tiles (same image object, modified extra_data)
    """
    if not hasattr(image, 'extra_data') or not image.extra_data:
        return image
    
    animation_data = image.extra_data
    if not isinstance(animation_data, dict) or 'states' not in animation_data:
        return image
    
    # Collect all tiles with their hash and metadata
    tile_hashes = {}  # hash -> first occurrence tile data
    tile_replacements = {}  # duplicate_tile_id -> first_tile_id
    
    total_tiles = 0
    duplicate_tiles = 0
    
    # Process all states and animations
    for state_index, state in enumerate(animation_data['states']):
        for animation_index, animation in enumerate(state.get('animations', [])):
            for frame_index, frame in enumerate(animation.get('frames', [])):
                for tile_index, tile in enumerate(frame.get('tiles', [])):
                    total_tiles += 1
                    
                    # Extract tile image data
                    tile_id = tile.get('id', f"tile_{total_tiles}")
                    slice_x = tile.get('sliceX', 0)
                    slice_y = tile.get('sliceY', 0)
                    
                    # Get tile dimensions (assuming 8x16 default)
                    tile_width = 8
                    tile_height = 16
                    
                    try:
                        # Extract tile from the processed image
                        tile_img = image.crop((slice_x, slice_y, slice_x + tile_width, slice_y + tile_height))
                        
                        # Create hash of tile pixel data
                        tile_hash = _create_tile_hash(tile_img)
                        
                        if tile_hash in tile_hashes:
                            # Found a duplicate tile
                            duplicate_tiles += 1
                            first_tile_id = tile_hashes[tile_hash]['id']
                            tile_replacements[tile_id] = first_tile_id
                            
                            # Replace duplicate tile with reference to first tile
                            _replace_tile_with_reference(tile, tile_hashes[tile_hash])
                        else:
                            # First occurrence of this tile
                            tile_hashes[tile_hash] = {
                                'id': tile_id,
                                'sliceX': slice_x,
                                'sliceY': slice_y,
                                'tile_img': tile_img
                            }
                    
                    except Exception as e:
                        print(f"Warning: Could not process tile {tile_id}: {e}")
                        continue
    
    # Update the image's extra_data with deduplication info
    if 'deduplication' not in animation_data:
        animation_data['deduplication'] = {}
    
    animation_data['deduplication'] = {
        'total_tiles': total_tiles,
        'unique_tiles': len(tile_hashes),
        'duplicate_tiles': duplicate_tiles,
        'memory_saved': duplicate_tiles,
        'tile_replacements': tile_replacements
    }
    
    return image


def _create_tile_hash(tile_img: Image.Image) -> str:
    """
    Create a hash of the tile image data for comparison.
    
    Args:
        tile_img: PIL Image tile
        
    Returns:
        String hash of the tile data
    """
    # Convert to RGB if needed
    if tile_img.mode != 'RGB':
        tile_img = tile_img.convert('RGB')
    
    # Get pixel data as bytes
    pixel_data = tile_img.tobytes()
    
    # Create hash
    return hashlib.md5(pixel_data).hexdigest()


def _replace_tile_with_reference(duplicate_tile: Dict[str, Any], first_tile: Dict[str, Any]) -> None:
    """
    Replace a duplicate tile with a reference to the first occurrence.
    
    Args:
        duplicate_tile: The duplicate tile to replace
        first_tile: The first occurrence tile to reference
    """
    # Store original data for reference
    duplicate_tile['_original_id'] = duplicate_tile.get('id')
    duplicate_tile['_original_sliceX'] = duplicate_tile.get('sliceX')
    duplicate_tile['_original_sliceY'] = duplicate_tile.get('sliceY')
    
    # Replace with reference to first tile
    duplicate_tile['id'] = first_tile['id']
    duplicate_tile['sliceX'] = first_tile['sliceX']
    duplicate_tile['sliceY'] = first_tile['sliceY']
    
    # Add deduplication flag
    duplicate_tile['_deduplicated'] = True
    duplicate_tile['_references'] = first_tile['id']
