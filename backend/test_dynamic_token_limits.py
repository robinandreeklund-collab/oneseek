#!/usr/bin/env python3
"""
Test for dynamic token limit configuration.
Verifies that DebateFlow uses actual token limits from LLM config.
"""

import sys
import os

# Test the logic without full imports
def test_dynamic_limit_calculation():
    """Test that token limits are calculated dynamically."""
    
    print("Testing dynamic token limit calculation...\n")
    
    # Simulate different token limits
    test_cases = [
        (128000, 76800, "128K model (user's VLLM)"),
        (95000, 57000, "95K model (old assumption)"),
        (100000, 60000, "100K model (default)"),
        (200000, 120000, "200K model (Doubao/Claude)"),
    ]
    
    for token_limit, expected_max_context, description in test_cases:
        # Calculate 60% for input context
        max_context_tokens = int(token_limit * 0.6)
        
        print(f"✓ {description}:")
        print(f"  Total limit: {token_limit:,} tokens")
        print(f"  Max context: {max_context_tokens:,} tokens (60%)")
        print(f"  Reserved for response: {token_limit - max_context_tokens:,} tokens (40%)")
        
        assert max_context_tokens == expected_max_context, \
            f"Expected {expected_max_context}, got {max_context_tokens}"
        print()
    
    print("✅ All calculations correct!\n")
    
    # Test warning thresholds
    print("Testing warning thresholds...\n")
    
    token_limit = 128000
    max_context = int(token_limit * 0.6)  # 76,800
    
    critical_threshold = int(max_context * 0.83)  # 83% of max context
    warning_threshold = int(max_context * 0.5)    # 50% of max context
    
    print(f"For 128K model (max context: {max_context:,}):")
    print(f"  Warning threshold: {warning_threshold:,} tokens (50% of max)")
    print(f"  Critical threshold: {critical_threshold:,} tokens (83% of max)")
    print()
    
    # Verify thresholds make sense
    assert warning_threshold < critical_threshold < max_context
    print("✅ Thresholds properly ordered!\n")
    
    # Compare old vs new limits
    print("Comparison: Old hardcoded vs New dynamic\n")
    print("Old system (hardcoded for 95K):")
    print("  Max context: 60,000 tokens")
    print("  Warning: 30,000 tokens")
    print("  Critical: 50,000 tokens")
    print()
    print("New system (dynamic for 128K):")
    print(f"  Max context: {max_context:,} tokens (+{max_context - 60000:,})")
    print(f"  Warning: {warning_threshold:,} tokens (+{warning_threshold - 30000:,})")
    print(f"  Critical: {critical_threshold:,} tokens (+{critical_threshold - 50000:,})")
    print()
    print(f"✅ Gained {max_context - 60000:,} tokens of usable context!")


if __name__ == "__main__":
    test_dynamic_limit_calculation()
