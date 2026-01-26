#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Test script to verify enable_thinking configuration for Qwen3/vLLM.
This script tests the configure_llm_with_thinking function.
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

def test_configure_llm_with_thinking():
    """Test that configure_llm_with_thinking works correctly."""
    from deer_flow.llms.llm import get_llm_by_type, configure_llm_with_thinking
    
    print("Testing configure_llm_with_thinking function...")
    
    # Test 1: Get a basic LLM instance
    try:
        llm = get_llm_by_type("basic")
        print(f"✓ Successfully got basic LLM: {type(llm).__name__}")
    except Exception as e:
        print(f"✗ Failed to get basic LLM: {e}")
        return False
    
    # Test 2: Configure with enable_thinking=True
    try:
        configured_llm = configure_llm_with_thinking(llm, enable_thinking=True, locale="sv-SE")
        print(f"✓ Successfully configured LLM with enable_thinking=True")
        print(f"  Configured LLM type: {type(configured_llm).__name__}")
    except Exception as e:
        print(f"✗ Failed to configure LLM with enable_thinking=True: {e}")
        return False
    
    # Test 3: Configure with enable_thinking=False
    try:
        configured_llm = configure_llm_with_thinking(llm, enable_thinking=False, locale="en-US")
        print(f"✓ Successfully configured LLM with enable_thinking=False")
    except Exception as e:
        print(f"✗ Failed to configure LLM with enable_thinking=False: {e}")
        return False
    
    print("\n✓ All tests passed!")
    return True

def test_locale_mapping():
    """Test that Swedish locale mapping works."""
    print("\nTesting Swedish locale mapping...")
    
    # This would be tested in the frontend, but we can verify the backend accepts sv-SE
    from deer_flow.prompts.template import get_prompt_template
    
    try:
        # Try to get a Swedish prompt template
        prompt = get_prompt_template("planner", "sv-SE")
        print("✓ Successfully loaded Swedish (sv-SE) prompt template")
        print(f"  Template preview: {prompt[:100]}...")
    except Exception as e:
        print(f"✗ Failed to load Swedish prompt template: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Enable Thinking Configuration Test")
    print("=" * 60)
    
    success = True
    
    # Test 1: Configure LLM with thinking
    if not test_configure_llm_with_thinking():
        success = False
    
    # Test 2: Locale mapping
    if not test_locale_mapping():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        sys.exit(1)
