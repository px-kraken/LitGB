import json
import uuid
from typing import Optional, Dict, Any

from PIL import Image

from algorithms import _spr_png_to_gbstudio_anim_o1, spr_rgb_to_3color_layers
from misc.arg_parse import argdict


def process(image: Image.Image, gbsres_data: Optional[Dict[str, Any]] = None, params: str = "") -> Image.Image:
    """
    Process an image for GB Studio animation generation using an optional GBSRES file as starting point.
    
    Args:
        image: PIL Image to process
        gbsres_data: Optional GBSRES data to use as starting point (preserves ID and other metadata)
        params: Parameter string for configuration
        
    Returns:
        Processed PIL Image with extra_data containing JSON metadata
    """
    if not isinstance(image, Image.Image):
        raise TypeError("image must be a PIL Image object")
    
    args = argdict(params)

    fname = args.setdefault('fname', 'sprite')
    enable_rgb = args.setdefault('rgb', 'n') == 'y'
    enable_processing = args.setdefault('processing', 'TBD') == 'True'

    # Apply RGB processing if requested
    if enable_rgb:
        image = spr_rgb_to_3color_layers.process(image)

    # Process the image for GB Studio animation
    processed_image = _spr_png_to_gbstudio_anim_o1.process(image, params)

    # Set save flag based on RGB processing
    processed_image.no_save = not enable_rgb

    if enable_processing:
        # If we have GBSRES data as starting point, preserve important metadata
        if gbsres_data and isinstance(gbsres_data, dict):
            # Preserve key metadata from the original GBSRES file
            preserved_fields = [
                "_resourceType", "id", "name", "symbol", 
                "filename", "checksum", "width", "height"
            ]
            
            for field in preserved_fields:
                if field in gbsres_data:
                    processed_image.extra_data[field] = gbsres_data[field]
            
            # Update filename to match the new sprite
            processed_image.extra_data["filename"] = f"{fname}.png"
            processed_image.extra_data["name"] = fname
            processed_image.extra_data["symbol"] = f"sprite_{fname.replace(' ', '_')}"
        else:
            # Ensure the name is properly set even without GBSRES template
            processed_image.extra_data["name"] = fname
            processed_image.extra_data["filename"] = f"{fname}.png"
            processed_image.extra_data["symbol"] = f"sprite_{fname.replace(' ', '_')}"

    return processed_image


def load_gbsres_file(gbsres_file) -> Optional[Dict[str, Any]]:
    """
    Load and parse a GBSRES file.
    
    Args:
        gbsres_file: File-like object containing GBSRES data
        
    Returns:
        Parsed JSON data or None if loading fails
    """
    try:
        if hasattr(gbsres_file, 'read'):
            # File-like object
            content = gbsres_file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
        else:
            # String content
            content = gbsres_file
            
        return json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as e:
        print(f"Warning: Could not load GBSRES file: {e}")
        return None
