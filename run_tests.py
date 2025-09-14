#!/usr/bin/env python3
"""
Test runner for the GB Studio Sprite Animator Streamlit app.
Runs all test suites and provides a summary.
"""

import unittest
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_all_tests():
    """Run all test suites and return results."""
    print("🧪 Running GB Studio Sprite Animator Tests")
    print("=" * 60)
    
    test_suites = [
        ("RGB to 3-Color Layers", "test_spr_rgb_to_3color_layers"),
        ("GB Studio Animation O1", "test_spr_png_to_gbstudio_anim_o1"), 
        ("GB Studio Animation with GBSRES", "test_spr_png_to_gbstudio_anim")
    ]
    
    total_tests = 0
    total_failures = 0
    results = []
    
    for suite_name, module_name in test_suites:
        print(f"\n📋 Running {suite_name} tests...")
        print("-" * 40)
        
        try:
            # Import and run the test module
            module = __import__(module_name)
            
            # Create test suite
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(module)
            
            # Run tests
            runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, 'w'))
            result = runner.run(suite)
            
            # Collect results
            tests_run = result.testsRun
            failures = len(result.failures) + len(result.errors)
            
            total_tests += tests_run
            total_failures += failures
            
            status = "✅ PASSED" if failures == 0 else "❌ FAILED"
            results.append((suite_name, tests_run, failures, status))
            
            print(f"{status} - {tests_run} tests, {failures} failures")
            
        except Exception as e:
            print(f"❌ ERROR - Failed to run {suite_name}: {e}")
            results.append((suite_name, 0, 1, "❌ ERROR"))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    for suite_name, tests_run, failures, status in results:
        print(f"{status} {suite_name}: {tests_run} tests, {failures} failures")
    
    print("-" * 60)
    overall_status = "✅ ALL TESTS PASSED" if total_failures == 0 else "❌ SOME TESTS FAILED"
    print(f"{overall_status}")
    print(f"Total: {total_tests} tests, {total_failures} failures")
    
    return total_failures == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
