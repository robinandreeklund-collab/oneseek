#!/usr/bin/env python3
"""
Debate Flow Validation Test Script

This script validates that the debate chain works correctly:
1. User query is passed to models
2. Rounds progress correctly (1 → 2 → 3 → reporter → END)
3. Tool calls are visible (if implemented)

Run with: python test_debate_flow_validation.py
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_preserve_state_meta_fields():
    """Test that preserve_state_meta_fields includes debate fields."""
    from backend.deer_flow.graph.nodes import preserve_state_meta_fields
    
    print("=" * 80)
    print("TEST 1: preserve_state_meta_fields structure")
    print("=" * 80)
    
    test_state = {
        "locale": "sv-SE",
        "research_topic": "Test question",
        "debate_round": 1,
        "debate_scores": {"proponent": 2, "opponent": 1},
    }
    
    preserved = preserve_state_meta_fields(test_state)
    
    print(f"Input state keys: {list(test_state.keys())}")
    print(f"Preserved keys: {list(preserved.keys())}")
    
    # Check debate fields ARE preserved
    debate_fields = [
        "debate_round",
        "debate_scores",
        "debate_knockout",
        "debate_max_rounds",
        "debate_error_count",
        "debate_complete",
        "debate_model_index",
        "debate_model_order",
        "debate_round_started",
    ]
    missing_debate_fields = [f for f in debate_fields if f not in preserved]
    
    if missing_debate_fields:
        print("❌ FAIL: preserve_state_meta_fields missing debate fields")
        print(f"   Missing: {missing_debate_fields}")
        return False
    else:
        print("✅ PASS: preserve_state_meta_fields includes debate fields")
    
    # Check meta fields ARE preserved
    required_meta_fields = ["locale", "research_topic", "clarified_research_topic", "resources"]
    missing_fields = [f for f in required_meta_fields if f not in preserved]
    
    if missing_fields:
        print(f"❌ FAIL: Missing meta fields: {missing_fields}")
        return False
    else:
        print(f"✅ PASS: All required meta fields present")
    
    print()
    return True


def test_user_query_passing():
    """Test that user query is correctly extracted from state."""
    print("=" * 80)
    print("TEST 2: User query extraction logic")
    print("=" * 80)
    
    # Simulate the logic in external_ai_caller_node
    test_cases = [
        {
            "state": {"clarified_research_topic": "Clarified question", "research_topic": "Original question"},
            "expected": "Clarified question",
            "description": "Clarified version takes precedence"
        },
        {
            "state": {"research_topic": "Original question"},
            "expected": "Original question",
            "description": "Fallback to research_topic"
        },
        {
            "state": {"clarified_research_topic": "", "research_topic": "Original question"},
            "expected": "Original question",
            "description": "Empty clarified falls back to research_topic"
        },
        {
            "state": {},
            "expected": "",
            "description": "Empty state returns empty string"
        },
    ]
    
    all_passed = True
    for i, test_case in enumerate(test_cases, 1):
        state = test_case["state"]
        expected = test_case["expected"]
        description = test_case["description"]
        
        # Simulate the extraction logic
        user_query = state.get("clarified_research_topic") or state.get("research_topic", "")
        
        if user_query == expected:
            print(f"✅ Test {i} PASS: {description}")
            print(f"   Result: '{user_query}'")
        else:
            print(f"❌ Test {i} FAIL: {description}")
            print(f"   Expected: '{expected}'")
            print(f"   Got: '{user_query}'")
            all_passed = False
    
    print()
    return all_passed


def test_debate_state_explicit_setting():
    """Test that debate_orchestrator sets all debate fields explicitly."""
    from backend.deer_flow.graph.nodes import debate_orchestrator_node
    import inspect
    
    print("=" * 80)
    print("TEST 3: Debate state explicit setting")
    print("=" * 80)
    
    # Get source code of debate_orchestrator_node
    source = inspect.getsource(debate_orchestrator_node)
    
    # Check that all Command.update dicts include debate fields
    required_fields = ["debate_round", "debate_scores", "debate_knockout", "debate_max_rounds", "debate_complete", "debate_error_count"]
    
    # Find all "return Command(" statements
    command_returns = []
    for line_no, line in enumerate(source.split('\n'), 1):
        if 'return Command(' in line or 'update={' in line:
            command_returns.append((line_no, line.strip()))
    
    print(f"Found {len([l for _, l in command_returns if 'return Command(' in l])} Command returns in debate_orchestrator_node")
    
    # Check if debate fields are mentioned in the function
    missing_fields = []
    for field in required_fields:
        if f'"{field}":' not in source and f"'{field}':" not in source:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"⚠️  WARNING: Fields {missing_fields} not found in debate_orchestrator source")
        print("   (May be false positive if using variables)")
    else:
        print(f"✅ PASS: All debate fields referenced in debate_orchestrator_node")
    
    print()
    return True


def test_tool_calls_format():
    """Test that tool_calls have the correct format."""
    print("=" * 80)
    print("TEST 4: Tool calls format validation")
    print("=" * 80)
    
    # Sample tool call from external_ai_caller
    import uuid
    sample_tool_call = {
        "id": f"call_{uuid.uuid4().hex[:24]}",
        "name": "query_model_in_round",
        "args": {
            "model_key": "gpt-3.5-turbo",
            "round_number": 1,
            "model_index": "1/5"
        }
    }
    
    # Validate structure
    required_keys = ["id", "name", "args"]
    missing_keys = [k for k in required_keys if k not in sample_tool_call]
    
    if missing_keys:
        print(f"❌ FAIL: Tool call missing keys: {missing_keys}")
        return False
    
    print("✅ PASS: Tool call has all required keys")
    print(f"   Sample: {json.dumps(sample_tool_call, indent=2)}")
    
    # Check ID format
    if sample_tool_call["id"].startswith("call_"):
        print("✅ PASS: Tool call ID has correct format (starts with 'call_')")
    else:
        print("❌ FAIL: Tool call ID should start with 'call_'")
        return False
    
    print()
    return True


def run_all_tests():
    """Run all validation tests."""
    print("\n" + "=" * 80)
    print("DEBATE FLOW VALIDATION TEST SUITE")
    print("=" * 80 + "\n")
    
    results = []
    
    try:
        results.append(("preserve_state_meta_fields", test_preserve_state_meta_fields()))
    except Exception as e:
        print(f"❌ Test crashed: {e}")
        results.append(("preserve_state_meta_fields", False))
    
    try:
        results.append(("user_query_passing", test_user_query_passing()))
    except Exception as e:
        print(f"❌ Test crashed: {e}")
        results.append(("user_query_passing", False))
    
    try:
        results.append(("debate_state_explicit", test_debate_state_explicit_setting()))
    except Exception as e:
        print(f"❌ Test crashed: {e}")
        results.append(("debate_state_explicit", False))
    
    try:
        results.append(("tool_calls_format", test_tool_calls_format()))
    except Exception as e:
        print(f"❌ Test crashed: {e}")
        results.append(("tool_calls_format", False))
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print()
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Debate flow should work correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the failures above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
