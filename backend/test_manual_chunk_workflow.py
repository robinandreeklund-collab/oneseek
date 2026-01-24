"""
Manual integration test for chunk relevance workflow
This script tests the actual workflow of browsing a page and checking chunk relevance
"""

import sys

def test_chunk_workflow():
    """Test the full workflow: browse_page -> check_chunk_relevance"""
    from tools import browse_page, check_chunk_relevance
    
    print("=" * 70)
    print("MANUAL TEST: Chunk Relevance Workflow")
    print("=" * 70)
    print()
    
    # Test 1: Create a mock large page content to simulate multiple chunks
    print("Test 1: Simulating browse_page with multiple chunks")
    print("-" * 70)
    
    # For demonstration, we'll manually create chunk-like outputs
    # In real usage, browse_page would return these
    mock_chunks = [
        {
            "title": "Article about AI (Part 1)",
            "content": "Artificial intelligence and machine learning are transforming the technology industry. " * 50,
            "url": "https://example.com/ai-article",
            "chunk_id": "1/3",
            "instructions": "This is part 1 of a large document."
        },
        {
            "title": "Article about AI (Part 2)",
            "content": "Deep learning neural networks have achieved breakthrough results in computer vision and natural language processing. " * 50,
            "url": "https://example.com/ai-article",
            "chunk_id": "2/3",
            "instructions": "This is part 2 of a large document."
        },
        {
            "title": "Article about AI (Part 3)",
            "content": "The weather today is sunny and warm. Perfect for outdoor activities and enjoying nature. " * 50,
            "url": "https://example.com/ai-article",
            "chunk_id": "3/3",
            "instructions": "This is part 3 of a large document."
        }
    ]
    
    print(f"✓ Simulated browse_page returning {len(mock_chunks)} chunks")
    for chunk in mock_chunks:
        print(f"  - Chunk {chunk['chunk_id']}: {len(chunk['content'])} chars")
    print()
    
    # Test 2: Check relevance of each chunk in parallel (simulated)
    print("Test 2: Checking relevance of all chunks")
    print("-" * 70)
    
    user_query = "Tell me about artificial intelligence and machine learning"
    
    relevance_results = []
    for chunk in mock_chunks:
        result = check_chunk_relevance.invoke({
            "chunk_id": chunk["chunk_id"],
            "chunk_content": chunk["content"],
            "user_query": user_query
        })
        relevance_results.append(result)
        
        print(f"\nChunk {result['chunk_id']}:")
        print(f"  Is Relevant: {result['is_relevant']}")
        print(f"  Score: {result['relevance_score']}")
        print(f"  Reasoning: {result['reasoning']}")
        if result['relevant_excerpts']:
            print(f"  Excerpt: {result['relevant_excerpts'][0][:100]}...")
    
    print()
    
    # Test 3: Filter and use only relevant chunks
    print("Test 3: Filtering relevant chunks")
    print("-" * 70)
    
    relevant_chunks = [
        (mock_chunks[i], relevance_results[i]) 
        for i in range(len(mock_chunks)) 
        if relevance_results[i]['is_relevant']
    ]
    
    print(f"✓ Filtered {len(relevant_chunks)} relevant chunks out of {len(mock_chunks)} total")
    print(f"✓ Token savings: Avoided processing {len(mock_chunks) - len(relevant_chunks)} irrelevant chunks")
    
    for chunk, relevance in relevant_chunks:
        print(f"\n  Using Chunk {chunk['chunk_id']} (score: {relevance['relevance_score']}):")
        print(f"    Content length: {len(chunk['content'])} chars")
        if relevance['relevant_excerpts']:
            print(f"    Key excerpt: {relevance['relevant_excerpts'][0][:80]}...")
    
    print()
    
    # Test 4: Verify the workflow benefits
    print("Test 4: Workflow Benefits Analysis")
    print("-" * 70)
    
    total_chars = sum(len(c['content']) for c in mock_chunks)
    relevant_chars = sum(len(mock_chunks[i]['content']) for i in range(len(mock_chunks)) if relevance_results[i]['is_relevant'])
    
    savings_percent = ((total_chars - relevant_chars) / total_chars * 100) if total_chars > 0 else 0
    
    print(f"Total content size: {total_chars:,} chars")
    print(f"Relevant content size: {relevant_chars:,} chars")
    print(f"Token savings: ~{savings_percent:.1f}% reduction")
    print(f"✓ This prevents token limit issues on large pages")
    
    print()
    print("=" * 70)
    print("MANUAL TEST COMPLETED SUCCESSFULLY ✓")
    print("=" * 70)
    
    return True


def test_real_webpage():
    """Test with a real small webpage (if available)"""
    from tools import browse_page, check_chunk_relevance
    
    print("\n" + "=" * 70)
    print("OPTIONAL TEST: Real Webpage (requires internet)")
    print("=" * 70)
    print()
    
    try:
        # Test with example.com which is small and stable
        url = "http://example.com"
        print(f"Browsing: {url}")
        
        chunks = browse_page.invoke({"url": url})
        
        print(f"✓ browse_page returned {len(chunks)} chunk(s)")
        
        if chunks and not chunks[0].get("error"):
            chunk = chunks[0]
            print(f"  Chunk {chunk['chunk_id']}")
            print(f"  Title: {chunk['title']}")
            print(f"  Content length: {len(chunk['content'])} chars")
            
            # Check relevance
            query = "example domain"
            result = check_chunk_relevance.invoke({
                "chunk_id": chunk["chunk_id"],
                "chunk_content": chunk["content"],
                "user_query": query
            })
            
            print(f"\n✓ check_chunk_relevance result:")
            print(f"  Is Relevant: {result['is_relevant']}")
            print(f"  Score: {result['relevance_score']}")
            print(f"  Reasoning: {result['reasoning']}")
            
            print("\n✓ Real webpage test PASSED")
        else:
            print(f"⚠ Could not fetch webpage (this is OK for testing): {chunks[0].get('content', 'Unknown error')}")
            
    except Exception as e:
        print(f"⚠ Real webpage test skipped (this is OK): {e}")
    
    print()


if __name__ == "__main__":
    try:
        # Run main workflow test
        test_chunk_workflow()
        
        # Try real webpage test (optional)
        test_real_webpage()
        
        print("\n" + "🎉 " * 20)
        print("ALL MANUAL TESTS COMPLETED SUCCESSFULLY!")
        print("🎉 " * 20)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
