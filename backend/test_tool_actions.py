"""
Test tool action tracking functionality
"""

def test_tool_name_mapping():
    """Test that tool name mapping returns correct display names and colors"""
    from agent_graph import OneSeekGraphAgent
    
    # Test mapping function
    display_name, icon, color = OneSeekGraphAgent._map_tool_name("tavily_search")
    assert display_name == "web_search", f"Expected 'web_search', got '{display_name}'"
    assert icon == "🔍", f"Expected '🔍', got '{icon}'"
    assert color == "blue", f"Expected 'blue', got '{color}'"
    print("✓ tavily_search maps to web_search (blue)")
    
    display_name, icon, color = OneSeekGraphAgent._map_tool_name("browse_page")
    assert display_name == "browse_page", f"Expected 'browse_page', got '{display_name}'"
    assert icon == "🌐", f"Expected '🌐', got '{icon}'"
    assert color == "green", f"Expected 'green', got '{color}'"
    print("✓ browse_page maps correctly (green)")
    
    display_name, icon, color = OneSeekGraphAgent._map_tool_name("smhi_weather_forecast")
    assert display_name == "smhi_api", f"Expected 'smhi_api', got '{display_name}'"
    assert icon == "🌤️", f"Expected '🌤️', got '{icon}'"
    assert color == "purple", f"Expected 'purple', got '{color}'"
    print("✓ smhi_weather_forecast maps to smhi_api (purple)")
    
    # Test unknown tool
    display_name, icon, color = OneSeekGraphAgent._map_tool_name("unknown_tool")
    assert display_name == "unknown_tool", f"Expected 'unknown_tool', got '{display_name}'"
    assert icon == "🔧", f"Expected '🔧', got '{icon}'"
    assert color == "gray", f"Expected 'gray', got '{color}'"
    print("✓ unknown tools default to gray")

def test_agent_state_has_tool_actions():
    """Test that AgentState includes tool_actions field"""
    from agent_graph import AgentState
    
    # Check that tool_actions is in the TypedDict annotations
    assert 'tool_actions' in AgentState.__annotations__, "AgentState should have tool_actions field"
    print("✓ AgentState includes tool_actions field")

if __name__ == "__main__":
    print("Testing Tool Action Tracking...")
    print("-" * 50)
    
    try:
        test_tool_name_mapping()
        print()
        test_agent_state_has_tool_actions()
        print()
        print("=" * 50)
        print("All tests passed! ✓")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
