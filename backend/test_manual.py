#!/usr/bin/env python3
"""
Manual test script for multi-tool LangGraph integration
Run this to manually verify the agent works correctly
"""

import json
from agent_graph import get_agent_graph

def test_agent_basic():
    """Test basic agent functionality without external services"""
    print("="*60)
    print("Testing OneSeek Multi-Tool Agent")
    print("="*60)
    
    # Get agent instance
    print("\n1. Initializing agent...")
    agent = get_agent_graph()
    print(f"   ✓ Agent initialized")
    print(f"   - vLLM URL: {agent.vllm_url}")
    print(f"   - vLLM Model: {agent.vllm_model}")
    
    # Test message structure
    print("\n2. Testing message structure...")
    messages = [
        {"role": "user", "content": "Hello, can you help me with AI topics?"}
    ]
    print(f"   ✓ Test messages created")
    
    # Test state initialization
    print("\n3. Testing state initialization...")
    try:
        from langchain_core.messages import HumanMessage
        lc_messages = [HumanMessage(content=msg["content"]) for msg in messages]
        initial_state = {
            "messages": lc_messages,
            "retrieved_docs": [],
            "steps": [],
            "system_prompt": None,
            "enable_thinking": False
        }
        print(f"   ✓ State initialized successfully")
    except Exception as e:
        print(f"   ✗ State initialization failed: {e}")
        return False
    
    print("\n4. Agent structure:")
    print(f"   - Graph compiled: {agent.graph is not None}")
    print(f"   - LLM initialized: {agent.llm is not None}")
    print(f"   - LLM with tools: {agent.llm_with_tools is not None}")
    
    print("\n" + "="*60)
    print("Basic tests completed successfully!")
    print("="*60)
    
    print("\nNote: Full integration test requires:")
    print("  - Running vLLM server at", agent.vllm_url)
    print("  - Optional: TAVILY_API_KEY for web search")
    print("  - Optional: Vespa configuration for RAG")
    print("\nTo test with a real query, ensure vLLM is running and use:")
    print("  python -c \"from agent_graph import get_agent_graph; agent = get_agent_graph(); result = agent.run([{'role': 'user', 'content': 'What is AI?'}]); print(result['content'])\"")
    
    return True


if __name__ == "__main__":
    import sys
    success = test_agent_basic()
    sys.exit(0 if success else 1)
