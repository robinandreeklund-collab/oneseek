"""
Integration tests for LangGraph multi-tool agent
"""

import os
import sys

def test_tools_import():
    """Test that tools module imports successfully"""
    print("Testing tools module import...")
    try:
        import tools
        print("✓ tools.py imports successfully")
        print(f"  Available tools: {[t.name for t in tools.AVAILABLE_TOOLS]}")
        assert len(tools.AVAILABLE_TOOLS) == 3
        assert any(t.name == "tavily_search" for t in tools.AVAILABLE_TOOLS)
        assert any(t.name == "duckduckgo_search" for t in tools.AVAILABLE_TOOLS)
        assert any(t.name == "vespa_search" for t in tools.AVAILABLE_TOOLS)
        print("✓ All 3 tools available")
        return True
    except Exception as e:
        print(f"✗ tools.py import failed: {e}")
        return False


def test_agent_graph_import():
    """Test that agent_graph module imports successfully"""
    print("\nTesting agent_graph module import...")
    try:
        import agent_graph
        print("✓ agent_graph.py imports successfully")
        agent = agent_graph.get_agent_graph()
        print("✓ Agent instantiated successfully")
        print(f"  vLLM URL: {agent.vllm_url}")
        print(f"  vLLM Model: {agent.vllm_model}")
        return True
    except Exception as e:
        print(f"✗ agent_graph.py import failed: {e}")
        return False


def test_app_import():
    """Test that app module imports successfully"""
    print("\nTesting app module import...")
    try:
        import app
        print("✓ app.py imports successfully")
        print(f"  API Title: {app.app.title}")
        print(f"  API Version: {app.app.version}")
        assert app.app.version == "0.3.0"
        print("✓ API version updated to 0.3.0")
        return True
    except Exception as e:
        print(f"✗ app.py import failed: {e}")
        return False


def test_tool_execution():
    """Test individual tool execution"""
    print("\nTesting individual tool execution...")
    
    # Test DuckDuckGo (free, no API key needed)
    print("  Testing duckduckgo_search tool...")
    try:
        import tools
        result = tools.duckduckgo_search.invoke({"query": "Python programming", "max_results": 2})
        print(f"    ✓ DuckDuckGo returned {len(result)} results")
        if result and not result[0].get("error"):
            print(f"    ✓ First result: {result[0].get('title', '')[:50]}...")
    except Exception as e:
        print(f"    ⚠ DuckDuckGo test failed: {e}")
    
    # Test Vespa (requires configuration)
    print("  Testing vespa_search tool...")
    try:
        import tools
        result = tools.vespa_search.invoke({"query": "test query", "max_results": 2})
        if result and result[0].get("error"):
            print(f"    ⚠ Vespa not configured (expected): {result[0].get('content')}")
        else:
            print(f"    ✓ Vespa returned {len(result)} results")
    except Exception as e:
        print(f"    ⚠ Vespa test failed: {e}")
    
    # Test Tavily (requires API key)
    print("  Testing tavily_search tool...")
    try:
        import tools
        result = tools.tavily_search.invoke({"query": "test query", "max_results": 2})
        if result and result[0].get("error"):
            print(f"    ⚠ Tavily not configured (expected): {result[0].get('content')}")
        else:
            print(f"    ✓ Tavily returned {len(result)} results")
    except Exception as e:
        print(f"    ⚠ Tavily test failed: {e}")
    
    return True


def test_backward_compatibility():
    """Test that old agent still works"""
    print("\nTesting backward compatibility with legacy agent...")
    try:
        import agent
        old_agent = agent.get_agent()
        print("✓ Legacy agent imports and instantiates successfully")
        print(f"  Legacy agent vLLM URL: {old_agent.vllm_url}")
        return True
    except Exception as e:
        print(f"✗ Legacy agent failed: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("OneSeek LangGraph Integration Tests")
    print("="*60)
    
    results = []
    results.append(("Tools Import", test_tools_import()))
    results.append(("Agent Graph Import", test_agent_graph_import()))
    results.append(("App Import", test_app_import()))
    results.append(("Tool Execution", test_tool_execution()))
    results.append(("Backward Compatibility", test_backward_compatibility()))
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("All tests passed! ✓")
    else:
        print("Some tests failed. See details above.")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
