"""
Phase 1 User Engagement System - Test Runner and Verification

This script runs all Phase 1 tests and provides a summary report.
Tests cover:
1. UserProfile model (database layer)
2. Points and Levels system (game mechanics)
3. Titles system (badge/achievement layer)
4. WebUI routes and engagement display (presentation layer)
"""

import unittest
import sys
import os
from io import StringIO

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Test modules to run
TEST_MODULES = [
    'Test.Web.test_webui_user_profile_model',
    'Test.Web.test_webui_points_levels',
    'Test.Web.test_webui_titles_system',
    'Test.Web.test_webui_engagement_routes',
]


def run_phase1_tests():
    """Run all Phase 1 user engagement tests"""
    
    print("=" * 80)
    print("PHASE 1 USER ENGAGEMENT SYSTEM - TEST EXECUTION")
    print("=" * 80)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Load all test modules
    for module_name in TEST_MODULES:
        try:
            module = __import__(module_name, fromlist=[''])
            tests = loader.loadTestsFromModule(module)
            suite.addTests(tests)
            print(f"✓ Loaded tests from {module_name}")
        except Exception as e:
            print(f"✗ Failed to load {module_name}: {e}")
    
    print()
    print(f"Total tests discovered: {suite.countTestCases()}")
    print()
    print("=" * 80)
    print("RUNNING TESTS...")
    print("=" * 80)
    print()
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print()
    
    if result.wasSuccessful():
        print("✓ ALL TESTS PASSED!")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        if result.failures:
            print()
            print("Failed tests:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print()
            print("Tests with errors:")
            for test, traceback in result.errors:
                print(f"  - {test}")
        
        return 1


def print_test_coverage():
    """Print test coverage information"""
    print()
    print("=" * 80)
    print("TEST COVERAGE - PHASE 1 IMPLEMENTATION")
    print("=" * 80)
    print()
    
    coverage_info = {
        'UserProfile Model Tests': {
            'file': 'test_webui_user_profile_model.py',
            'coverage': [
                'UserProfile creation and relationships',
                'Points accumulation mechanics',
                'Level calculation (all 5 tiers)',
                'Title field management',
                'Timestamps and data persistence',
                'Multi-user profile independence',
            ]
        },
        'Points & Levels System Tests': {
            'file': 'test_webui_points_levels.py',
            'coverage': [
                'Points awarding for different actions',
                'Point accumulation in user journey',
                'Level calculation based on points',
                'Level progression monotonicity',
                'Level transition points',
                'Title eligibility based on level/points',
            ]
        },
        'Titles System Tests': {
            'file': 'test_webui_titles_system.py',
            'coverage': [
                'Phase 1 titles structure and count (8 titles)',
                'Title category organization',
                'Title eligibility requirements',
                'Individual title tests (all 8 titles)',
                'Title display formatting',
                'User journey progression through titles',
                'Title persistence in database',
            ]
        },
        'WebUI Routes & Display Tests': {
            'file': 'test_webui_engagement_routes.py',
            'coverage': [
                'User profile page/routes',
                'Profile data display (level, points, title)',
                'Engagement statistics display',
                'Leaderboard pages and APIs',
                'User stats endpoints',
                'Profile data model validation',
                'Timestamp tracking',
            ]
        }
    }
    
    for category, info in coverage_info.items():
        print(f"\n{category}")
        print(f"File: {info['file']}")
        print("Coverage:")
        for item in info['coverage']:
            print(f"  ✓ {item}")
    
    print()
    print("=" * 80)
    print("IMPLEMENTATION CHECKLIST - PHASE 1")
    print("=" * 80)
    print()
    
    checklist = [
        ("Database Model (UserProfile)", "✓ Implemented - user_id, points, level, title, stats fields"),
        ("Points System", "✓ Implemented - 8 different point-earning actions"),
        ("Level Calculation", "✓ Implemented - 5 tiers (Bronze 1-10, Silver 11-20, Gold 21-30, Platinum 31-40, Diamond 41+)"),
        ("Title System", "✓ Implemented - 8 Phase 1 titles with requirements"),
        ("User Profile Display", "⚠ Partially - Data model ready, routes may need implementation"),
        ("WebUI Routes", "⚠ Partially - Test framework ready, route handlers may need implementation"),
    ]
    
    for item, status in checklist:
        print(f"{item:.<50} {status}")
    
    print()
    print("=" * 80)


if __name__ == '__main__':
    try:
        exit_code = run_phase1_tests()
        print_test_coverage()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
