"""
Test that streaming includes tool_actions in the metadata
"""
import json

def test_streaming_format():
    """Test that the streaming format includes tool_actions"""
    
    # Simulate what the backend would send
    metadata = {
        "steps": ["Analyzing query", "Calling tools: browse_page"],
        "retrieved": [],
        "source_count": 0,
        "tool_actions": [
            {
                "tool_name": "browse_page",
                "display_name": "browse_page",
                "icon": "🌐",
                "color": "green",
                "input": {"url": "https://example.com"},
                "output": [{"title": "Example", "content": "Test"}],
                "start_time": 1234567890.0,
                "end_time": 1234567891.5,
                "duration": 1.5,
                "status": "completed"
            }
        ]
    }
    
    # Format as AI SDK would expect (data annotation format)
    stream_line = f"2:{json.dumps([metadata])}\n"
    
    print("Testing streaming format...")
    print("-" * 50)
    print("Stream line (AI SDK format):")
    print(stream_line)
    print()
    
    # Verify it can be parsed
    prefix, data_json = stream_line.split(":", 1)
    assert prefix == "2", "Should be data annotation (type 2)"
    
    data = json.loads(data_json.strip())
    assert isinstance(data, list), "Data should be a list"
    assert len(data) == 1, "Should have one metadata object"
    
    parsed_metadata = data[0]
    assert "tool_actions" in parsed_metadata, "Metadata should include tool_actions"
    assert isinstance(parsed_metadata["tool_actions"], list), "tool_actions should be a list"
    assert len(parsed_metadata["tool_actions"]) == 1, "Should have one tool action"
    
    tool_action = parsed_metadata["tool_actions"][0]
    assert tool_action["display_name"] == "browse_page", "Display name should be browse_page"
    assert tool_action["color"] == "green", "Color should be green"
    assert tool_action["icon"] == "🌐", "Icon should be 🌐"
    assert tool_action["status"] == "completed", "Status should be completed"
    assert tool_action["duration"] == 1.5, "Duration should be 1.5"
    
    print("✓ Stream format is correct")
    print("✓ tool_actions can be parsed")
    print("✓ All fields are present")
    print()
    print("=" * 50)
    print("Streaming format test passed! ✓")

if __name__ == "__main__":
    test_streaming_format()
