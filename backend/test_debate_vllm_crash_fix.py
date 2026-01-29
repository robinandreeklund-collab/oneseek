#!/usr/bin/env python3
"""
Test for debate flow search result summarization fix.
Verifies that large search results are properly truncated.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.debate_flow import DebateFlow


def test_summarize_search_results_with_list():
    """Test that list search results are properly summarized and limited."""
    debate_flow = DebateFlow()
    
    # Simulate large search results from Tavily
    large_results = [
        {
            "title": "Very long title " * 50,  # 800+ chars
            "content": "Very long content " * 100,  # 1800+ chars
            "url": "http://example.com",
            "raw_content": "Extremely long raw content " * 200,  # 5400+ chars
        },
        {
            "title": "Another title",
            "content": "Another content " * 50,
        },
        {
            "title": "Third title",
            "content": "Third content",
        }
    ]
    
    # Test with default max_chars (500)
    summary = debate_flow._summarize_search_results(large_results)
    print(f"Test 1: List results with default limit")
    print(f"  Summary length: {len(summary)} chars")
    print(f"  Summary preview: {summary[:100]}...")
    
    assert len(summary) <= 500, f"Summary too long: {len(summary)} chars (expected <= 500)"
    assert "Sökresultat:" in summary, "Should start with 'Sökresultat:'"
    print("  ✓ Test passed\n")
    
    # Test with custom max_chars (200)
    summary_small = debate_flow._summarize_search_results(large_results, max_chars=200)
    print(f"Test 2: List results with 200 char limit")
    print(f"  Summary length: {len(summary_small)} chars")
    assert len(summary_small) <= 200, f"Summary too long: {len(summary_small)} chars (expected <= 200)"
    print("  ✓ Test passed\n")


def test_summarize_search_results_with_dict():
    """Test that dict search results are properly handled."""
    debate_flow = DebateFlow()
    
    # Simulate dict result with answer field
    dict_result = {
        "answer": "Short answer to the question " * 50,  # 1500+ chars
        "results": [],
        "other_data": "x" * 10000,  # Huge field
    }
    
    summary = debate_flow._summarize_search_results(dict_result, max_chars=300)
    print(f"Test 3: Dict result with answer field")
    print(f"  Summary length: {len(summary)} chars")
    print(f"  Summary preview: {summary[:100]}...")
    
    assert len(summary) <= 300, f"Summary too long: {len(summary)} chars (expected <= 300)"
    print("  ✓ Test passed\n")


def test_summarize_search_results_nested():
    """Test that nested structures are handled."""
    debate_flow = DebateFlow()
    
    # Simulate nested structure
    nested_result = {
        "results": [
            {"title": "Title 1", "content": "Content 1 " * 100},
            {"title": "Title 2", "content": "Content 2 " * 100},
        ]
    }
    
    summary = debate_flow._summarize_search_results(nested_result, max_chars=400)
    print(f"Test 4: Nested dict with results array")
    print(f"  Summary length: {len(summary)} chars")
    
    assert len(summary) <= 400, f"Summary too long: {len(summary)} chars (expected <= 400)"
    print("  ✓ Test passed\n")


def test_summarize_huge_string():
    """Test that huge string conversion is limited."""
    debate_flow = DebateFlow()
    
    # Create a huge object that would be thousands of chars when str()
    huge_obj = {"data": "x" * 50000}
    
    summary = debate_flow._summarize_search_results(huge_obj, max_chars=100)
    print(f"Test 5: Huge object string conversion")
    print(f"  Summary length: {len(summary)} chars")
    
    assert len(summary) <= 100, f"Summary too long: {len(summary)} chars (expected <= 100)"
    print("  ✓ Test passed\n")


def test_empty_results():
    """Test empty results don't cause issues."""
    debate_flow = DebateFlow()
    
    summary_empty_list = debate_flow._summarize_search_results([])
    print(f"Test 6: Empty list")
    print(f"  Summary: '{summary_empty_list}'")
    assert summary_empty_list == "Inga resultat"
    print("  ✓ Test passed\n")
    
    summary_empty_dict = debate_flow._summarize_search_results({})
    print(f"Test 7: Empty dict")
    print(f"  Summary: '{summary_empty_dict}'")
    assert len(summary_empty_dict) <= 500
    print("  ✓ Test passed\n")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing Search Result Summarization (VLLM Crash Fix)")
    print("=" * 70)
    print()
    
    try:
        test_summarize_search_results_with_list()
        test_summarize_search_results_with_dict()
        test_summarize_search_results_nested()
        test_summarize_huge_string()
        test_empty_results()
        
        print("=" * 70)
        print("✓ All tests passed!")
        print("=" * 70)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
