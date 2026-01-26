#!/usr/bin/env python3
"""
Simple test to verify Tier-3 structure works.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all modules can be imported."""
    try:
        from envelope_consumers.consumer import create_consumer
        from semantic_processors.processor import SemanticProcessor
        from scoring_engines.scorer import MonetizationScorer
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_consumer_creation():
    """Test envelope consumer creation."""
    try:
        from envelope_consumers.consumer import create_consumer
        consumer = create_consumer()
        assert consumer is not None
        print("✅ Consumer creation successful")
        return True
    except Exception as e:
        print(f"❌ Consumer creation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== TIER-3 SIMPLE TESTS ===")
    print()
    
    tests = [
        test_imports,
        test_consumer_creation,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print()
    print("=== TEST SUMMARY ===")
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} tests passed!")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print(f"❌ {total - passed} tests failed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
