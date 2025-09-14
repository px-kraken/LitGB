"""
Test suite for spr_png_to_gbstudio_anim.py - GB Studio animation generation with GBSRES template support.

Tests the core GB Studio animation processing functionality including:
- PNG processing with optional GBSRES template
- Metadata preservation from GBSRES files
- JSON structure generation
- RGB processing integration
"""

import unittest
import os
import json
import tempfile
from PIL import Image

# Import the module to test
from algorithms.spr_png_to_gbstudio_anim import process, load_gbsres_file


class TestSprPngToGBStudioAnim(unittest.TestCase):
    """Test cases for spr_png_to_gbstudio_anim.py - GB Studio animation generation with GBSRES template support."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_image_path = "input/test/assets/sprites/chicken_fighter_full.png"
        self.test_gbsres_path = "input/test/project/sprites/chicken_fighter_full.gbsres"
        self.test_image = None
        self.test_gbsres_data = None
        
        if os.path.exists(self.test_image_path):
            self.test_image = Image.open(self.test_image_path)
        
        if os.path.exists(self.test_gbsres_path):
            with open(self.test_gbsres_path, 'r') as f:
                self.test_gbsres_data = json.load(f)
    
    def test_process_without_gbsres_template(self):
        """Test processing without GBSRES template."""
        if not self.test_image:
            self.skipTest("Test image not available")
        
        params = "fname=test_sprite processing=True rgb=n twidth=8 theight=16 htiles=1 vtiles=1 states=fixed palettes=1"
        result = process(self.test_image, None, params)
        
        # Check that result is a PIL Image
        self.assertIsInstance(result, Image.Image)
        
        # Check that extra_data contains JSON structure
        self.assertIsInstance(result.extra_data, dict)
        self.assertIn('_resourceType', result.extra_data)
        self.assertEqual(result.extra_data['_resourceType'], 'sprite')
        
        # Check that new metadata was generated
        self.assertIn('id', result.extra_data)
        self.assertIn('name', result.extra_data)
        self.assertEqual(result.extra_data['name'], 'test_sprite')
    
    def test_process_with_gbsres_template(self):
        """Test processing with GBSRES template."""
        if not self.test_image or not self.test_gbsres_data:
            self.skipTest("Test image or GBSRES data not available")
        
        params = "fname=new_sprite processing=True rgb=n twidth=8 theight=16 htiles=1 vtiles=1 states=fixed palettes=1"
        result = process(self.test_image, self.test_gbsres_data, params)
        
        # Check that result is a PIL Image
        self.assertIsInstance(result, Image.Image)
        
        # Check that extra_data contains JSON structure
        self.assertIsInstance(result.extra_data, dict)
        self.assertIn('_resourceType', result.extra_data)
        self.assertEqual(result.extra_data['_resourceType'], 'sprite')
        
        # Check that metadata from template was preserved
        self.assertEqual(result.extra_data['id'], self.test_gbsres_data['id'])
        self.assertEqual(result.extra_data['_resourceType'], self.test_gbsres_data['_resourceType'])
        
        # Check that filename was updated
        self.assertEqual(result.extra_data['name'], 'new_sprite')
        self.assertEqual(result.extra_data['filename'], 'new_sprite.png')
        self.assertEqual(result.extra_data['symbol'], 'sprite_new_sprite')
    
    def test_process_with_rgb_conversion(self):
        """Test processing with RGB conversion."""
        if not self.test_image:
            self.skipTest("Test image not available")
        
        params = "fname=test_sprite processing=True rgb=y twidth=8 theight=16 htiles=1 vtiles=1 states=fixed palettes=1"
        result = process(self.test_image, None, params)
        
        # Check that result is a PIL Image
        self.assertIsInstance(result, Image.Image)
        
        # Check that RGB processing was applied (no_save should be False when rgb=True)
        self.assertTrue(hasattr(result, 'no_save'))
        self.assertFalse(result.no_save)
    
    def test_process_without_rgb_conversion(self):
        """Test processing without RGB conversion."""
        if not self.test_image:
            self.skipTest("Test image not available")
        
        params = "fname=test_sprite processing=True rgb=n twidth=8 theight=16 htiles=1 vtiles=1 states=fixed palettes=1"
        result = process(self.test_image, None, params)
        
        # Check that result is a PIL Image
        self.assertIsInstance(result, Image.Image)
        
        # Check that no_save flag is set when rgb=False
        self.assertTrue(hasattr(result, 'no_save'))
        self.assertTrue(result.no_save)
    
    def test_load_gbsres_file_valid(self):
        """Test loading a valid GBSRES file."""
        if not self.test_gbsres_data:
            self.skipTest("Test GBSRES data not available")
        
        # Create a temporary file with GBSRES data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.gbsres', delete=False) as f:
            json.dump(self.test_gbsres_data, f)
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'r') as f:
                result = load_gbsres_file(f)
            
            self.assertIsNotNone(result)
            self.assertIsInstance(result, dict)
            self.assertEqual(result['_resourceType'], 'sprite')
            self.assertEqual(result['id'], self.test_gbsres_data['id'])
        finally:
            os.unlink(temp_file_path)
    
    def test_load_gbsres_file_invalid(self):
        """Test loading an invalid GBSRES file."""
        # Test with invalid JSON
        result = load_gbsres_file('{"invalid": json}')
        self.assertIsNone(result)
        
        # Test with non-JSON content
        result = load_gbsres_file('not json content')
        self.assertIsNone(result)
    
    def test_process_different_state_types(self):
        """Test processing with different animation state types."""
        if not self.test_image:
            self.skipTest("Test image not available")
        
        state_types = ["fixed", "multi", "multi_movement", "multi#f", "multi_movement#f"]
        
        for state_type in state_types:
            with self.subTest(state_type=state_type):
                params = f"fname=test_{state_type} processing=True rgb=n twidth=8 theight=16 htiles=1 vtiles=1 states={state_type} palettes=1"
                result = process(self.test_image, None, params)
                
                self.assertIsInstance(result, Image.Image)
                self.assertIsInstance(result.extra_data, dict)
                self.assertIn('states', result.extra_data)
                self.assertGreater(len(result.extra_data['states']), 0)
    
    def test_process_tile_configuration(self):
        """Test different tile configurations."""
        if not self.test_image:
            self.skipTest("Test image not available")
        
        # Test different tile sizes
        tile_configs = [
            (8, 16, 1, 1),   # 8x16, 1x1 tiles per frame
            (16, 16, 2, 1),  # 16x16, 2x1 tiles per frame
            (8, 8, 1, 2),    # 8x8, 1x2 tiles per frame
        ]
        
        for twidth, theight, htiles, vtiles in tile_configs:
            with self.subTest(twidth=twidth, theight=theight, htiles=htiles, vtiles=vtiles):
                params = f"fname=test_{twidth}x{theight} processing=True rgb=n twidth={twidth} theight={theight} htiles={htiles} vtiles={vtiles} states=fixed palettes=1"
                result = process(self.test_image, None, params)
                
                self.assertIsInstance(result, Image.Image)
                self.assertIsInstance(result.extra_data, dict)
                
                # Check canvas dimensions
                expected_canvas_width = htiles * twidth
                expected_canvas_height = vtiles * theight
                self.assertEqual(result.extra_data["canvasWidth"], expected_canvas_width)
                self.assertEqual(result.extra_data["canvasHeight"], expected_canvas_height)
    
    def test_process_error_handling_invalid_image(self):
        """Test error handling for invalid image type."""
        with self.assertRaises(TypeError):
            process("not_an_image", None, "")
        
        with self.assertRaises(TypeError):
            process(None, None, "")


def run_tests():
    """Run all tests."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test class
    tests = unittest.TestLoader().loadTestsFromTestCase(TestSprPngToGBStudioAnim)
    test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("Running GB Studio animation processing tests...")
    print("=" * 60)
    
    success = run_tests()
    
    if success:
        print("\n" + "=" * 60)
        print("All tests passed! ✅")
    else:
        print("\n" + "=" * 60)
        print("Some tests failed! ❌")
        
    print(f"\nTest files used:")
    print(f"- Input image: input/test/assets/sprites/chicken_fighter_full.png")
    print(f"- GBSRES template: input/test/project/sprites/chicken_fighter_full.gbsres")
