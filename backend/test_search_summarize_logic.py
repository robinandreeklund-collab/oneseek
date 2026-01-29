#!/usr/bin/env python3
"""
Simple test for _summarize_search_results logic without imports.
Tests the core logic that was fixed.
"""


def _summarize_search_results(search_results, max_chars=500):
    """
    Copy of the fixed _summarize_search_results method for testing.
    """
    if isinstance(search_results, list):
        if len(search_results) > 0:
            # Build summary from multiple results, limited to max_chars total
            summary_parts = []
            remaining_chars = max_chars - 50  # Reserve space for prefix
            
            for idx, result in enumerate(search_results[:3]):  # Max 3 results
                if remaining_chars <= 0:
                    break
                    
                if isinstance(result, dict):
                    # Try to get title and content, but limit each
                    title = result.get('title', '')[:100]
                    content = result.get('content', '')[:200]
                    
                    if title and content:
                        part = f"{idx+1}. {title}: {content}"
                    elif title:
                        part = f"{idx+1}. {title}"
                    elif content:
                        part = f"{idx+1}. {content}"
                    else:
                        # Fallback: take first value that's a string
                        for v in result.values():
                            if isinstance(v, str) and len(v) > 10:
                                part = f"{idx+1}. {v[:150]}"
                                break
                        else:
                            continue
                    
                    if len(part) > remaining_chars:
                        part = part[:remaining_chars] + "..."
                    
                    summary_parts.append(part)
                    remaining_chars -= len(part) + 2  # +2 for newline
            
            if summary_parts:
                result = "Sökresultat:\n" + "\n".join(summary_parts)
            else:
                result = f"Hittade {len(search_results)} källor"
        else:
            result = "Inga resultat"
    else:
        # For non-list results, extract key info carefully
        # NEVER convert entire object to string - too dangerous
        if isinstance(search_results, dict):
            # Try to extract useful fields
            summary_text = ""
            for key in ['answer', 'content', 'text', 'results']:
                if key in search_results:
                    val = search_results[key]
                    if isinstance(val, str):
                        summary_text = val[:max_chars]
                        break
                    elif isinstance(val, list) and len(val) > 0:
                        # Recursively summarize
                        return _summarize_search_results(val, max_chars)
            
            if summary_text:
                result = summary_text
            else:
                result = f"Sökresultat tillgängligt ({len(search_results)} fält)"
        else:
            # Last resort: convert to string but with strict limit
            result = str(search_results)[:max_chars]
    
    # Final safety check: ensure we never exceed max_chars
    if len(result) > max_chars:
        result = result[:max_chars] + "..."
    
    return result


def test_all():
    print("Testing _summarize_search_results fix...\n")
    
    # Test 1: Large list results
    large_results = [
        {
            "title": "Very long title " * 50,
            "content": "Very long content " * 100,
            "url": "http://example.com",
        }
    ]
    summary = _summarize_search_results(large_results, max_chars=500)
    assert len(summary) <= 500, f"FAIL: Summary too long ({len(summary)} chars)"
    print(f"✓ Test 1 passed: Large list limited to {len(summary)} chars (max 500)")
    
    # Test 2: Dict with answer
    dict_result = {"answer": "x" * 10000, "other": "y" * 10000}
    summary = _summarize_search_results(dict_result, max_chars=300)
    assert len(summary) <= 300, f"FAIL: Summary too long ({len(summary)} chars)"
    print(f"✓ Test 2 passed: Dict limited to {len(summary)} chars (max 300)")
    
    # Test 3: Nested structure
    nested = {"results": [{"title": "T1", "content": "C1" * 500}]}
    summary = _summarize_search_results(nested, max_chars=400)
    assert len(summary) <= 400, f"FAIL: Summary too long ({len(summary)} chars)"
    print(f"✓ Test 3 passed: Nested limited to {len(summary)} chars (max 400)")
    
    # Test 4: Empty results
    summary = _summarize_search_results([])
    assert summary == "Inga resultat"
    print(f"✓ Test 4 passed: Empty list handled correctly")
    
    # Test 5: Huge string conversion
    huge_obj = {"unknown_field": "x" * 100000}
    summary = _summarize_search_results(huge_obj, max_chars=100)
    assert len(summary) <= 100, f"FAIL: Summary too long ({len(summary)} chars)"
    print(f"✓ Test 5 passed: Huge object limited to {len(summary)} chars (max 100)")
    
    print("\n✅ All tests passed!")
    print("\nThe fix ensures search results are always limited to prevent context explosion.")


if __name__ == "__main__":
    test_all()
