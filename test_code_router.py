#!/usr/bin/env python3
"""
Test script for code router and tools functionality.
"""

import os
import sys
import logging

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_code_detection():
    """Test code question detection."""
    from backend.deer_flow.graph.nodes import is_code_related_question
    
    test_cases = [
        ("Write a Python function to sort a list", True),
        ("How do I create a React component?", True),
        ("What is the weather today?", False),
        ("Debug my JavaScript code", True),
        ("Tell me about AI", False),
        ("Build a Next.js app", True),
        ("What is quantum computing?", False),
        ("Fix this Python error", True),
    ]
    
    logger.info("Testing code question detection...")
    passed = 0
    failed = 0
    
    for question, expected in test_cases:
        result = is_code_related_question(question)
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        logger.info(f"{status} '{question}' -> {result} (expected {expected})")
    
    logger.info(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_tool_imports():
    """Test that code tools can be imported."""
    logger.info("Testing code tool imports...")
    
    try:
        from backend.deer_flow.tools.code_tools import (
            linux_sandbox_tool,
            file_system_tool,
            react_sandbox_tool,
            get_code_tools
        )
        logger.info("✓ All code tools imported successfully")
        
        # Test get_code_tools function
        tools = get_code_tools()
        logger.info(f"✓ get_code_tools() returned {len(tools)} tools")
        
        return True
    except ImportError as e:
        logger.error(f"✗ Failed to import code tools: {e}")
        return False


def test_tool_structure():
    """Test that tools have proper structure."""
    logger.info("Testing tool structure...")
    
    try:
        from backend.deer_flow.tools.code_tools import linux_sandbox_tool
        
        # Check if tool has required attributes
        assert hasattr(linux_sandbox_tool, 'name'), "Tool missing 'name' attribute"
        assert hasattr(linux_sandbox_tool, 'description'), "Tool missing 'description' attribute"
        assert callable(linux_sandbox_tool), "Tool is not callable"
        
        logger.info(f"✓ linux_sandbox_tool structure valid")
        logger.info(f"  Name: {linux_sandbox_tool.name}")
        logger.info(f"  Description: {linux_sandbox_tool.description[:100]}...")
        
        return True
    except Exception as e:
        logger.error(f"✗ Tool structure test failed: {e}")
        return False


def test_disabled_tools():
    """Test that disabled tools return appropriate messages."""
    logger.info("Testing disabled tools behavior...")
    
    try:
        # Ensure tools are disabled
        os.environ['ENABLE_LINUX_SANDBOX'] = 'false'
        os.environ['ENABLE_FILE_SYSTEM_TOOL'] = 'false'
        os.environ['ENABLE_REACT_SANDBOX'] = 'false'
        
        from backend.deer_flow.tools.code_tools import (
            linux_sandbox_tool,
            file_system_tool,
            react_sandbox_tool
        )
        
        # Test each tool returns disabled message
        result1 = linux_sandbox_tool.invoke({"command": "echo test"})
        assert "disabled" in result1.lower(), "Linux sandbox should be disabled"
        logger.info("✓ linux_sandbox_tool correctly disabled")
        
        result2 = file_system_tool.invoke({"operation": "read", "path": "test.txt"})
        assert "disabled" in result2.lower(), "File system tool should be disabled"
        logger.info("✓ file_system_tool correctly disabled")
        
        result3 = react_sandbox_tool.invoke({"action": "create", "project_name": "test"})
        assert "disabled" in result3.lower(), "React sandbox should be disabled"
        logger.info("✓ react_sandbox_tool correctly disabled")
        
        return True
    except Exception as e:
        logger.error(f"✗ Disabled tools test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Code Router and Tools Test Suite")
    logger.info("=" * 60)
    
    tests = [
        ("Code Detection", test_code_detection),
        ("Tool Imports", test_tool_imports),
        ("Tool Structure", test_tool_structure),
        ("Disabled Tools", test_disabled_tools),
    ]
    
    results = []
    for name, test_func in tests:
        logger.info(f"\n{'-' * 60}")
        logger.info(f"Running: {name}")
        logger.info(f"{'-' * 60}")
        
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status} - {name}")
    
    logger.info(f"\n{passed}/{total} test suites passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
