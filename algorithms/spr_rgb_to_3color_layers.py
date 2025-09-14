from PIL import Image
from typing import List, Tuple


def process(image: Image.Image, params: str = "") -> Image.Image:
    """
    Convert RGB image to 3-color layers for GB Studio.
    
    Given an image:
      1) Parse the FIRST ROW to extract color triplets separated by a green (0,255,0) break pixel.
      2) Discard the first 8 rows; consider the rest (from row 8 to bottom) as 'remaining image'.
      3) For each extracted color triplet, create a band (of height equal to the remaining image's height),
         and copy only pixels matching one of the triplet colors (mapping them to the new colors):
             c1 -> (224, 248, 207)
             c2 -> (134, 192, 108)
             c3 -> (7, 24, 33)
         All other pixels are skipped (transparent).
      4) Stack these bands vertically and return the final image.
    
    Args:
        image: PIL Image to process
        params: Parameter string (unused in this implementation)
        
    Returns:
        Processed PIL Image with color layers stacked vertically
        
    Raises:
        ValueError: If image height is too small to discard 8 rows
    """
    if not isinstance(image, Image.Image):
        raise TypeError("image must be a PIL Image object")
    
    # Ensure we're in RGB mode
    if image.mode != 'RGB':
        image = image.convert('RGB')

    width, height = image.size
    
    if width < 4:
        raise ValueError("Image width must be at least 4 pixels to contain color triplets")

    # Parse the first row to extract color triplets
    triplets = _extract_color_triplets(image, width)
    
    if not triplets:
        raise ValueError("No valid color triplets found in the first row")

    # Calculate remaining height after discarding first 8 rows
    rem_height = height - 8
    if rem_height <= 0:
        raise ValueError("Image height is too small to discard 8 rows and proceed.")

    # Create the result image with stacked bands
    return _create_stacked_bands(image, triplets, width, rem_height)


def _extract_color_triplets(image: Image.Image, width: int) -> List[Tuple[Tuple[int, int, int], ...]]:
    """Extract color triplets from the first row of the image."""
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


def _create_stacked_bands(image: Image.Image, triplets: List[Tuple[Tuple[int, int, int], ...]], 
                         width: int, rem_height: int) -> Image.Image:
    """Create stacked bands for each color triplet."""
    final_height = rem_height * len(triplets)
    result_img = Image.new('RGB', (width, final_height), (0, 255, 0))

    # Define the mapping from each color in the triplet to its new color
    mapped_colors = [(224, 248, 207), (134, 192, 108), (7, 24, 33)]

    for i, (col1, col2, col3) in enumerate(triplets):
        band_y_offset = i * rem_height
        
        # Process each row in the remaining image
        for row in range(rem_height):
            src_y = row + 8  # Source row in original image
            for x in range(width):
                pix = image.getpixel((x, src_y))

                # Map triplet colors to new colors
                if pix == col1:
                    new_pix = mapped_colors[0]
                elif pix == col2:
                    new_pix = mapped_colors[1]
                elif pix == col3:
                    new_pix = mapped_colors[2]
                else:
                    continue  # Skip non-matching pixels

                # Place the new pixel in the correct band row
                result_img.putpixel((x, band_y_offset + row), new_pix)

    return result_img
