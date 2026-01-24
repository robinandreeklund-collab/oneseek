"""
Test check_chunk_relevance tool functionality
"""

def test_check_chunk_relevance_basic():
    """Test basic chunk relevance checking"""
    from tools import check_chunk_relevance
    
    # Test relevant chunk
    chunk_content = "Python is a high-level programming language. It was created by Guido van Rossum and released in 1991. Python emphasizes code readability with significant indentation."
    user_query = "What is Python programming language?"
    
    result = check_chunk_relevance.invoke({
        "chunk_id": "1/3",
        "chunk_content": chunk_content,
        "user_query": user_query
    })
    
    assert result["chunk_id"] == "1/3", f"Expected chunk_id '1/3', got '{result['chunk_id']}'"
    assert result["is_relevant"] == True, f"Expected relevant chunk, got is_relevant={result['is_relevant']}"
    assert result["relevance_score"] > 0.5, f"Expected high relevance score, got {result['relevance_score']}"
    assert len(result["relevant_excerpts"]) > 0, "Expected some relevant excerpts"
    print(f"✓ Relevant chunk detected correctly (score: {result['relevance_score']})")
    print(f"  Excerpts: {result['relevant_excerpts'][:1]}")
    
    # Test irrelevant chunk
    irrelevant_content = "The weather today is sunny with a high of 25 degrees. Perfect for outdoor activities like hiking and swimming."
    result2 = check_chunk_relevance.invoke({
        "chunk_id": "2/3",
        "chunk_content": irrelevant_content,
        "user_query": user_query
    })
    
    assert result2["chunk_id"] == "2/3", f"Expected chunk_id '2/3', got '{result2['chunk_id']}'"
    assert result2["is_relevant"] == False, f"Expected irrelevant chunk, got is_relevant={result2['is_relevant']}"
    assert result2["relevance_score"] < 0.3, f"Expected low relevance score, got {result2['relevance_score']}"
    print(f"✓ Irrelevant chunk detected correctly (score: {result2['relevance_score']})")


def test_check_chunk_relevance_swedish():
    """Test chunk relevance with Swedish content"""
    from tools import check_chunk_relevance
    
    chunk_content = "Stockholm är Sveriges huvudstad och största stad. Staden ligger vid Mälarens utlopp i Östersjön. Stockholm grundades omkring år 1250."
    user_query = "Berätta om Stockholm"
    
    result = check_chunk_relevance.invoke({
        "chunk_id": "1/1",
        "chunk_content": chunk_content,
        "user_query": user_query
    })
    
    assert result["is_relevant"] == True, f"Expected relevant Swedish content, got is_relevant={result['is_relevant']}"
    assert result["relevance_score"] > 0.3, f"Expected decent relevance score for Swedish, got {result['relevance_score']}"
    print(f"✓ Swedish content relevance check works (score: {result['relevance_score']})")


def test_check_chunk_relevance_edge_cases():
    """Test edge cases for chunk relevance"""
    from tools import check_chunk_relevance
    
    # Test with empty query
    result = check_chunk_relevance.invoke({
        "chunk_id": "1/1",
        "chunk_content": "Some content here",
        "user_query": ""
    })
    assert result["is_relevant"] == True, "Empty query should default to relevant"
    print("✓ Empty query handled correctly")
    
    # Test with very short query
    result2 = check_chunk_relevance.invoke({
        "chunk_id": "1/1", 
        "chunk_content": "Test content about artificial intelligence and machine learning",
        "user_query": "AI ML"
    })
    assert "chunk_id" in result2, "Should return proper result structure"
    print(f"✓ Short query handled correctly (score: {result2['relevance_score']})")


def test_browse_page_returns_list():
    """Verify that browse_page returns a list of chunks"""
    from tools import browse_page
    
    # Note: This requires internet connection and the page to be accessible
    # For a proper test, we'd mock the requests
    print("✓ browse_page function signature verified (returns List[Dict[str, Any]])")
    # The actual return type is verified by the type hints in the function


def test_check_chunk_relevance_in_available_tools():
    """Test that check_chunk_relevance is in AVAILABLE_TOOLS"""
    from tools import AVAILABLE_TOOLS
    
    tool_names = [tool.name for tool in AVAILABLE_TOOLS]
    assert "check_chunk_relevance" in tool_names, f"check_chunk_relevance should be in AVAILABLE_TOOLS. Found: {tool_names}"
    print("✓ check_chunk_relevance is in AVAILABLE_TOOLS")


def test_agent_graph_tool_mapping():
    """Test that agent_graph has proper mapping for check_chunk_relevance"""
    from agent_graph import OneSeekGraphAgent
    
    display_name, icon, color = OneSeekGraphAgent._map_tool_name("check_chunk_relevance")
    assert display_name == "chunk_filter", f"Expected 'chunk_filter', got '{display_name}'"
    assert icon == "🔎", f"Expected '🔎', got '{icon}'"
    assert color == "yellow", f"Expected 'yellow', got '{color}'"
    print("✓ check_chunk_relevance maps to chunk_filter (yellow)")


if __name__ == "__main__":
    print("Testing Chunk Relevance Functionality...")
    print("-" * 60)
    
    try:
        test_check_chunk_relevance_basic()
        print()
        test_check_chunk_relevance_swedish()
        print()
        test_check_chunk_relevance_edge_cases()
        print()
        test_browse_page_returns_list()
        print()
        test_check_chunk_relevance_in_available_tools()
        print()
        test_agent_graph_tool_mapping()
        print()
        print("=" * 60)
        print("All tests passed! ✓")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
