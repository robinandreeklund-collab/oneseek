"""
Example: Using DeerFlow Integration in OneSeek

This example demonstrates how to use the DeerFlow-inspired multi-agent
architecture with OneSeek's VLLM backend.
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from langchain_core.messages import HumanMessage

# Import DeerFlow components
from deer_flow.llms import get_llm_by_type
from deer_flow.agents import create_researcher_agent, create_analyst_agent
from deer_flow.config import get_full_config, validate_config
from deer_flow.graph import create_simple_agent_workflow

# Import OneSeek tools
from tools import get_available_tools


def example_basic_usage():
    """Example: Basic LLM usage with VLLM."""
    print("=" * 60)
    print("Example 1: Basic LLM Usage")
    print("=" * 60)
    
    # Get VLLM-backed LLM
    llm = get_llm_by_type("basic")
    
    # Use like any LangChain LLM
    response = llm.invoke([HumanMessage(content="What is AI?")])
    print(f"Response: {response.content[:200]}...")
    print()


def example_specialized_agents():
    """Example: Using specialized agents."""
    print("=" * 60)
    print("Example 2: Specialized Agents")
    print("=" * 60)
    
    # Get available tools
    tools = get_available_tools()
    
    # Create specialized agents
    researcher = create_researcher_agent(tools)
    analyst = create_analyst_agent(tools)
    
    print(f"Created researcher agent with {len(tools)} tools")
    print(f"Created analyst agent with {len(tools)} tools")
    print()


def example_workflow():
    """Example: Using agent workflow."""
    print("=" * 60)
    print("Example 3: Agent Workflow")
    print("=" * 60)
    
    # Get tools
    tools = get_available_tools()
    
    # Create workflow
    workflow = create_simple_agent_workflow(tools)
    
    # Prepare state
    state = {
        "messages": [HumanMessage(content="What are the latest AI trends?")],
        "steps": [],
        "retrieved_docs": [],
        "tool_actions": []
    }
    
    print("Created workflow with agent and tools")
    print("Ready to process queries with tool calling")
    print()


def example_configuration():
    """Example: Configuration management."""
    print("=" * 60)
    print("Example 4: Configuration")
    print("=" * 60)
    
    # Get full configuration
    config = get_full_config()
    
    print(f"VLLM URL: {config['vllm']['url']}")
    print(f"VLLM Model: {config['vllm']['model']}")
    print(f"Vespa Enabled: {config['vespa']['enabled']}")
    print(f"Tavily Enabled: {config['search']['tavily_enabled']}")
    print(f"DuckDuckGo Enabled: {config['search']['duckduckgo_enabled']}")
    
    # Validate configuration
    is_valid, errors = validate_config()
    print(f"\nConfiguration valid: {is_valid}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("DeerFlow Integration Examples")
    print("=" * 60)
    print()
    
    try:
        # Check if VLLM is configured
        vllm_url = os.getenv("VLLM_URL")
        if not vllm_url:
            print("⚠️  Warning: VLLM_URL not configured")
            print("Set VLLM_URL environment variable to use these examples")
            print("Example: export VLLM_URL=http://localhost:8000/v1")
            print()
        
        # Run examples (some will work without VLLM running)
        example_configuration()
        example_specialized_agents()
        example_workflow()
        
        # This requires VLLM to be running
        if vllm_url:
            print("Note: To run the basic usage example, ensure VLLM is running")
            print("Uncomment the line below to test actual LLM calls")
            # example_basic_usage()
        
        print("=" * 60)
        print("Examples completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Ensure VLLM is running: vllm serve YOUR_MODEL --port 8000")
        print("2. Set environment variables in backend/.env")
        print("3. Use deer_flow components in your agent code")
        print("4. See backend/DEER_FLOW_INTEGRATION.md for detailed guide")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
