import unittest
import tempfile
import os
from PIL import Image
import sys

# Add the project root to the path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from algorithms.spr_rgb_to_3color_layers import process, _extract_color_triplets, _create_stacked_bands


class TestSprRgbTo3ColorLayers(unittest.TestCase):
    """Comprehensive test cases for spr_rgb_to_3color_layers module."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after each test method."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.test_dir)

    def create_test_image_with_triplets(self, width=16, height=20, num_triplets=2):
        """Create a test image with proper color triplets in the first row."""
        image = Image.new('RGB', (width, height), (0, 255, 0))  # Green background
        
        # Add color triplets to the first row
        for i in range(num_triplets):
            start_x = i * 4
            if start_x + 3 < width:
                # Set triplet colors
                image.putpixel((start_x, 0), (255, 0, 0))      # Red
                image.putpixel((start_x + 1, 0), (0, 0, 255))  # Blue
                image.putpixel((start_x + 2, 0), (255, 255, 0)) # Yellow
                image.putpixel((start_x + 3, 0), (0, 255, 0))   # Green break pixel
        
        # Add some test data in the remaining rows (after row 8)
        for y in range(8, height):
            for x in range(width):
                if x % 4 == 0 and x + 3 < width:
                    image.putpixel((x, y), (255, 0, 0))      # Red
                elif x % 4 == 1 and x + 2 < width:
                    image.putpixel((x, y), (0, 0, 255))      # Blue
                elif x % 4 == 2 and x + 1 < width:
                    image.putpixel((x, y), (255, 255, 0))    # Yellow
        
        return image

    def test_process_basic_functionality(self):
        """Test basic process function with valid input."""
        test_image = self.create_test_image_with_triplets(16, 20, 2)
        
        result = process(test_image)
        
        # Should return an Image
        self.assertIsInstance(result, Image.Image)
        # Should be in RGB mode
        self.assertEqual(result.mode, 'RGB')
        # Should have correct dimensions (width same, height = rem_height * num_triplets)
        expected_height = (20 - 8) * 2  # (height - 8) * num_triplets
        self.assertEqual(result.size, (16, expected_height))

    def test_process_with_different_image_modes(self):
        """Test process function with different image modes."""
        # Test with RGBA mode
        rgba_image = Image.new('RGBA', (16, 20), (0, 255, 0, 255))
        # Add color triplets
        for i in range(2):
            start_x = i * 4
            rgba_image.putpixel((start_x, 0), (255, 0, 0, 255))
            rgba_image.putpixel((start_x + 1, 0), (0, 0, 255, 255))
            rgba_image.putpixel((start_x + 2, 0), (255, 255, 0, 255))
            rgba_image.putpixel((start_x + 3, 0), (0, 255, 0, 255))
        
        result = process(rgba_image)
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.mode, 'RGB')

    def test_process_single_triplet(self):
        """Test process function with single color triplet."""
        test_image = self.create_test_image_with_triplets(8, 16, 1)
        
        result = process(test_image)
        
        self.assertIsInstance(result, Image.Image)
        expected_height = (16 - 8) * 1  # (height - 8) * num_triplets
        self.assertEqual(result.size, (8, expected_height))

    def test_process_multiple_triplets(self):
        """Test process function with multiple color triplets."""
        test_image = self.create_test_image_with_triplets(20, 24, 3)
        
        result = process(test_image)
        
        self.assertIsInstance(result, Image.Image)
        expected_height = (24 - 8) * 3  # (height - 8) * num_triplets
        self.assertEqual(result.size, (20, expected_height))

    def test_process_color_mapping(self):
        """Test that colors are correctly mapped to the expected values."""
        test_image = self.create_test_image_with_triplets(8, 16, 1)
        
        result = process(test_image)
        
        # Check that the mapped colors are present in the result
        mapped_colors = [(224, 248, 207), (134, 192, 108), (7, 24, 33)]
        result_colors = set()
        
        for y in range(result.height):
            for x in range(result.width):
                pixel = result.getpixel((x, y))
                if pixel != (0, 255, 0):  # Not background green
                    result_colors.add(pixel)
        
        # Should contain the mapped colors
        for mapped_color in mapped_colors:
            self.assertIn(mapped_color, result_colors)

    def test_process_error_handling_invalid_image_type(self):
        """Test error handling for invalid image type."""
        with self.assertRaises(TypeError):
            process("not_an_image")
        
        with self.assertRaises(TypeError):
            process(None)

    def test_process_error_handling_small_width(self):
        """Test error handling for image with width < 4."""
        small_image = Image.new('RGB', (3, 10), (0, 255, 0))
        
        with self.assertRaises(ValueError) as context:
            process(small_image)
        
        self.assertIn("Image width must be at least 4 pixels", str(context.exception))

    def test_process_error_handling_no_triplets(self):
        """Test error handling when no valid triplets are found."""
        # Create image with no valid triplets
        no_triplets_image = Image.new('RGB', (8, 16), (0, 255, 0))
        # Fill first row with non-triplet pattern
        for x in range(8):
            no_triplets_image.putpixel((x, 0), (128, 128, 128))
        
        with self.assertRaises(ValueError) as context:
            process(no_triplets_image)
        
        self.assertIn("No valid color triplets found", str(context.exception))

    def test_process_error_handling_small_height(self):
        """Test error handling for image with height <= 8."""
        small_height_image = Image.new('RGB', (8, 8), (0, 255, 0))
        # Add one triplet
        small_height_image.putpixel((0, 0), (255, 0, 0))
        small_height_image.putpixel((1, 0), (0, 0, 255))
        small_height_image.putpixel((2, 0), (255, 255, 0))
        small_height_image.putpixel((3, 0), (0, 255, 0))
        
        with self.assertRaises(ValueError) as context:
            process(small_height_image)
        
        self.assertIn("Image height is too small to discard 8 rows", str(context.exception))

    def test_extract_color_triplets_basic(self):
        """Test _extract_color_triplets function with valid input."""
        test_image = self.create_test_image_with_triplets(12, 16, 2)
        
        triplets = _extract_color_triplets(test_image, 12)
        
        self.assertEqual(len(triplets), 2)
        self.assertEqual(triplets[0], ((255, 0, 0), (0, 0, 255), (255, 255, 0)))
        self.assertEqual(triplets[1], ((255, 0, 0), (0, 0, 255), (255, 255, 0)))

    def test_extract_color_triplets_no_triplets(self):
        """Test _extract_color_triplets function with no valid triplets."""
        no_triplets_image = Image.new('RGB', (8, 16), (0, 255, 0))
        # Fill first row with non-triplet pattern
        for x in range(8):
            no_triplets_image.putpixel((x, 0), (128, 128, 128))
        
        triplets = _extract_color_triplets(no_triplets_image, 8)
        
        self.assertEqual(len(triplets), 0)

    def test_extract_color_triplets_starts_with_green(self):
        """Test _extract_color_triplets function when first pixel is green."""
        green_start_image = Image.new('RGB', (8, 16), (0, 255, 0))
        # First pixel is green, should stop immediately
        green_start_image.putpixel((0, 0), (0, 255, 0))
        
        triplets = _extract_color_triplets(green_start_image, 8)
        
        self.assertEqual(len(triplets), 0)

    def test_extract_color_triplets_partial_triplet(self):
        """Test _extract_color_triplets function with partial triplet at end."""
        partial_image = Image.new('RGB', (6, 16), (0, 255, 0))
        # Add one complete triplet
        partial_image.putpixel((0, 0), (255, 0, 0))
        partial_image.putpixel((1, 0), (0, 0, 255))
        partial_image.putpixel((2, 0), (255, 255, 0))
        partial_image.putpixel((3, 0), (0, 255, 0))
        # Add partial triplet (no break pixel)
        partial_image.putpixel((4, 0), (255, 0, 0))
        partial_image.putpixel((5, 0), (0, 0, 255))
        
        triplets = _extract_color_triplets(partial_image, 6)
        
        self.assertEqual(len(triplets), 1)  # Only the complete triplet

    def test_create_stacked_bands_basic(self):
        """Test _create_stacked_bands function with valid input."""
        test_image = self.create_test_image_with_triplets(8, 16, 2)
        triplets = _extract_color_triplets(test_image, 8)
        
        result = _create_stacked_bands(test_image, triplets, 8, 8)
        
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.mode, 'RGB')
        self.assertEqual(result.size, (8, 16))  # width * (rem_height * num_triplets)

    def test_create_stacked_bands_color_mapping(self):
        """Test _create_stacked_bands function color mapping."""
        # Create a simple test image
        test_image = Image.new('RGB', (4, 12), (0, 255, 0))
        # Add one triplet
        test_image.putpixel((0, 0), (255, 0, 0))      # Red
        test_image.putpixel((1, 0), (0, 0, 255))      # Blue
        test_image.putpixel((2, 0), (255, 255, 0))    # Yellow
        test_image.putpixel((3, 0), (0, 255, 0))      # Green break
        
        # Add some test pixels in the remaining rows
        test_image.putpixel((0, 8), (255, 0, 0))      # Red pixel
        test_image.putpixel((1, 9), (0, 0, 255))      # Blue pixel
        test_image.putpixel((2, 10), (255, 255, 0))   # Yellow pixel
        
        triplets = _extract_color_triplets(test_image, 4)
        result = _create_stacked_bands(test_image, triplets, 4, 4)
        
        # Check that colors are mapped correctly
        mapped_colors = [(224, 248, 207), (134, 192, 108), (7, 24, 33)]
        
        # Red should map to first color
        self.assertEqual(result.getpixel((0, 0)), mapped_colors[0])
        # Blue should map to second color
        self.assertEqual(result.getpixel((1, 1)), mapped_colors[1])
        # Yellow should map to third color
        self.assertEqual(result.getpixel((2, 2)), mapped_colors[2])

    def test_create_stacked_bands_empty_triplets(self):
        """Test _create_stacked_bands function with empty triplets list."""
        test_image = Image.new('RGB', (8, 16), (0, 255, 0))
        
        result = _create_stacked_bands(test_image, [], 8, 8)
        
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.size, (8, 0))  # height = rem_height * 0

    def test_process_edge_case_minimum_dimensions(self):
        """Test process function with minimum valid dimensions."""
        # Minimum width (4) and minimum height (9)
        min_image = Image.new('RGB', (4, 9), (0, 255, 0))
        # Add one triplet
        min_image.putpixel((0, 0), (255, 0, 0))
        min_image.putpixel((1, 0), (0, 0, 255))
        min_image.putpixel((2, 0), (255, 255, 0))
        min_image.putpixel((3, 0), (0, 255, 0))
        
        result = process(min_image)
        
        self.assertIsInstance(result, Image.Image)
        expected_height = (9 - 8) * 1  # (height - 8) * num_triplets
        self.assertEqual(result.size, (4, expected_height))

    def test_process_with_different_triplet_colors(self):
        """Test process function with different color combinations."""
        test_image = Image.new('RGB', (8, 16), (0, 255, 0))
        
        # Use different colors for the triplet
        test_image.putpixel((0, 0), (100, 200, 50))   # Custom color 1
        test_image.putpixel((1, 0), (200, 100, 150))  # Custom color 2
        test_image.putpixel((2, 0), (50, 150, 200))   # Custom color 3
        test_image.putpixel((3, 0), (0, 255, 0))      # Green break
        
        # Add matching pixels in remaining rows
        test_image.putpixel((0, 8), (100, 200, 50))   # Should map to first mapped color
        test_image.putpixel((1, 9), (200, 100, 150))  # Should map to second mapped color
        test_image.putpixel((2, 10), (50, 150, 200))  # Should map to third mapped color
        
        result = process(test_image)
        
        self.assertIsInstance(result, Image.Image)
        # Check that the custom colors were mapped correctly
        mapped_colors = [(224, 248, 207), (134, 192, 108), (7, 24, 33)]
        self.assertEqual(result.getpixel((0, 0)), mapped_colors[0])
        self.assertEqual(result.getpixel((1, 1)), mapped_colors[1])
        self.assertEqual(result.getpixel((2, 2)), mapped_colors[2])

    def test_process_background_color_preservation(self):
        """Test that background green color is preserved in result."""
        test_image = self.create_test_image_with_triplets(8, 16, 1)
        
        result = process(test_image)
        
        # Check that background areas (non-matching pixels) are still green
        # Look for a pixel that should be background (not matching any triplet color)
        background_found = False
        for y in range(result.height):
            for x in range(result.width):
                pixel = result.getpixel((x, y))
                if pixel == (0, 255, 0):  # Background green
                    background_found = True
                    break
            if background_found:
                break
        
        self.assertTrue(background_found, "Background green color should be preserved in non-matching areas")

    def test_process_params_parameter(self):
        """Test that params parameter is accepted but ignored."""
        test_image = self.create_test_image_with_triplets(8, 16, 1)
        
        # Should work with params parameter
        result1 = process(test_image, "")
        result2 = process(test_image, "some_params")
        
        # Results should be identical
        self.assertEqual(result1.size, result2.size)
        self.assertEqual(result1.mode, result2.mode)

    def test_process_large_image(self):
        """Test process function with larger image dimensions."""
        large_image = self.create_test_image_with_triplets(64, 100, 4)
        
        result = process(large_image)
        
        self.assertIsInstance(result, Image.Image)
        expected_height = (100 - 8) * 4  # (height - 8) * num_triplets
        self.assertEqual(result.size, (64, expected_height))

    def test_process_wide_image(self):
        """Test process function with wide image (many triplets)."""
        wide_image = self.create_test_image_with_triplets(40, 20, 8)  # 8 triplets
        
        result = process(wide_image)
        
        self.assertIsInstance(result, Image.Image)
        expected_height = (20 - 8) * 8  # (height - 8) * num_triplets
        self.assertEqual(result.size, (40, expected_height))

    def test_extract_color_triplets_edge_cases(self):
        """Test _extract_color_triplets function with various edge cases."""
        # Test with exactly 4 pixels (one triplet)
        small_image = Image.new('RGB', (4, 10), (0, 255, 0))
        small_image.putpixel((0, 0), (255, 0, 0))
        small_image.putpixel((1, 0), (0, 0, 255))
        small_image.putpixel((2, 0), (255, 255, 0))
        small_image.putpixel((3, 0), (0, 255, 0))
        
        triplets = _extract_color_triplets(small_image, 4)
        self.assertEqual(len(triplets), 1)
        self.assertEqual(triplets[0], ((255, 0, 0), (0, 0, 255), (255, 255, 0)))

    def test_create_stacked_bands_different_heights(self):
        """Test _create_stacked_bands function with different remaining heights."""
        test_image = Image.new('RGB', (8, 16), (0, 255, 0))
        # Add one triplet
        test_image.putpixel((0, 0), (255, 0, 0))
        test_image.putpixel((1, 0), (0, 0, 255))
        test_image.putpixel((2, 0), (255, 255, 0))
        test_image.putpixel((3, 0), (0, 255, 0))
        
        triplets = _extract_color_triplets(test_image, 8)
        result = _create_stacked_bands(test_image, triplets, 8, 5)  # Different rem_height
        
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.size, (8, 5))  # width * rem_height


if __name__ == '__main__':
    unittest.main(verbosity=2)
