#!/usr/bin/env python3
"""
Test script to verify the GB Studio sprite processing functionality
without requiring Streamlit to be installed.
"""

import sys
import os
from PIL import Image
import io

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from algorithms.spr_png_to_gbstudio_anim import process


def scale_image_for_display(image, max_width=400):
    """Scale an image using nearest neighbor interpolation for pixel art."""
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


def test_processing():
    """Test the sprite processing functionality."""
    print("🧪 Testing GB Studio Sprite Processing...")
    
    # Create a simple test image (32x32 pixels, green background)
    test_image = Image.new('RGB', (32, 32), (0, 255, 0))
    
    # Add some test pixels
    for x in range(8):
        for y in range(16):
            if (x + y) % 2 == 0:
                test_image.putpixel((x, y), (255, 0, 0))  # Red pixel
    
    print(f"✅ Created test image: {test_image.size}")
    
    # Test parameters
    params = "fname=test_sprite isref=True override=True processing=True rgb=y twidth=8 theight=16 htiles=1 vtiles=1 states=fixed palettes=1 chksum=TBD"
    
    try:
        # Process the image
        processed_image = process(test_image, params)
        print("✅ Image processing completed successfully!")
        
        # Check if we got JSON data
        if hasattr(processed_image, 'extra_data') and processed_image.extra_data:
            if isinstance(processed_image.extra_data, dict):
                print("✅ Generated JSON metadata:")
                print(f"   - Resource Type: {processed_image.extra_data.get('_resourceType', 'N/A')}")
                print(f"   - Name: {processed_image.extra_data.get('name', 'N/A')}")
                print(f"   - Frames: {processed_image.extra_data.get('numFrames', 'N/A')}")
                print(f"   - Tiles: {processed_image.extra_data.get('numTiles', 'N/A')}")
            else:
                print(f"✅ Processing message: {processed_image.extra_data}")
        
        # Test zip file creation
        zip_buffer = create_test_zip(processed_image, "test_sprite")
        print(f"✅ Created ZIP file ({len(zip_buffer.getvalue())} bytes)")
        
        # Test image scaling
        scaled_image = scale_image_for_display(processed_image)
        print(f"✅ Image scaling test: {processed_image.size} → {scaled_image.size}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during processing: {str(e)}")
        return False


def create_test_zip(processed_image, filename):
    """Create a test ZIP file with the proper folder structure."""
    import zipfile
    
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
                import json
                json_buffer = io.BytesIO()
                json_str = json.dumps(processed_image.extra_data, indent=2)
                json_buffer.write(json_str.encode('utf-8'))
                json_buffer.seek(0)
                zip_file.writestr(f"project/sprites/{filename}.gbsres", json_buffer.getvalue())
    
    zip_buffer.seek(0)
    return zip_buffer


def main():
    """Main test function."""
    print("🎮 GB Studio Sprite Animator - Test Suite")
    print("=" * 50)
    
    success = test_processing()
    
    print("=" * 50)
    if success:
        print("🎉 All tests passed! The app should work correctly.")
        print("\n📋 To run the Streamlit app:")
        print("1. Install Streamlit: pip install streamlit")
        print("2. Run the app: streamlit run app.py")
        print("3. Open your browser to http://localhost:8501")
    else:
        print("❌ Tests failed. Please check the error messages above.")
    
    return success


if __name__ == "__main__":
    main()
