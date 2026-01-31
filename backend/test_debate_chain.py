#!/usr/bin/env python3
"""
Test for the separate debate chain implementation.
Tests import and basic structure of debate nodes.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_debate_nodes_syntax():
    """Test that debate nodes have valid Python syntax"""
    print("\nTesting debate nodes syntax...")
    try:
        import py_compile
        import os
        
        test_dir = os.path.dirname(os.path.abspath(__file__))
        nodes_file = os.path.join(test_dir, 'deer_flow', 'graph', 'nodes.py')
        builder_file = os.path.join(test_dir, 'deer_flow', 'graph', 'builder.py')
        
        # Check syntax
        py_compile.compile(nodes_file, doraise=True)
        print(f"  ✓ nodes.py has valid syntax")
        
        py_compile.compile(builder_file, doraise=True)
        print(f"  ✓ builder.py has valid syntax")
        
        print("✓ All debate node files have valid Python syntax")
        return True
    except Exception as e:
        print(f"✗ Syntax check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_debate_agent_llm_map():
    """Test that debate agents are in AGENT_LLM_MAP"""
    print("\nTesting AGENT_LLM_MAP for debate agents...")
    try:
        from deer_flow.config.agents import AGENT_LLM_MAP
        
        debate_agents = [
            "debate_orchestrator",
            "proponent",
            "opponent",
            "fact_checker",
            "synthesizer",
            "moderator",
        ]
        
        missing = []
        for agent in debate_agents:
            if agent not in AGENT_LLM_MAP:
                missing.append(agent)
            else:
                print(f"  ✓ {agent}: {AGENT_LLM_MAP[agent]}")
        
        if missing:
            print(f"✗ Missing agents in AGENT_LLM_MAP: {missing}")
            return False
        
        print("✓ All debate agents in AGENT_LLM_MAP")
        return True
    except Exception as e:
        print(f"✗ AGENT_LLM_MAP test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_debate_prompts_exist():
    """Test that debate prompts exist"""
    print("\nTesting debate prompt files...")
    try:
        import os
        # Get the correct path relative to this test file
        test_dir = os.path.dirname(os.path.abspath(__file__))
        prompts_dir = os.path.join(test_dir, 'deer_flow', 'prompts')
        
        prompt_files = [
            "debate_orchestrator.sv_SE.md",
            "proponent.sv_SE.md",
            "opponent.sv_SE.md",
            "fact_checker.sv_SE.md",
            "synthesizer.sv_SE.md",
            "moderator.sv_SE.md",
        ]
        
        missing = []
        for prompt_file in prompt_files:
            full_path = os.path.join(prompts_dir, prompt_file)
            if not os.path.exists(full_path):
                missing.append(prompt_file)
            else:
                print(f"  ✓ {prompt_file} exists")
        
        if missing:
            print(f"✗ Missing prompt files: {missing}")
            return False
        
        print("✓ All debate prompt files exist")
        return True
    except Exception as e:
        print(f"✗ Prompt files test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_debate_nodes_in_files():
    """Test that debate node functions are defined in nodes.py"""
    print("\nTesting debate node function definitions...")
    try:
        import os
        
        test_dir = os.path.dirname(os.path.abspath(__file__))
        nodes_file = os.path.join(test_dir, 'deer_flow', 'graph', 'nodes.py')
        
        with open(nodes_file, 'r') as f:
            content = f.read()
        
        node_functions = [
            "debate_orchestrator_node",
            "proponent_node",
            "opponent_node",
            "fact_checker_node",
            "synthesizer_node",
            "moderator_node",
        ]
        
        missing = []
        for func in node_functions:
            if f"async def {func}" not in content:
                missing.append(func)
            else:
                print(f"  ✓ {func} defined in nodes.py")
        
        if missing:
            print(f"✗ Missing node functions: {missing}")
            return False
        
        print("✓ All debate node functions are defined")
        return True
    except Exception as e:
        print(f"✗ Node definition test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_debate_nodes_imported_in_builder():
    """Test that debate nodes are imported in builder.py"""
    print("\nTesting debate node imports in builder.py...")
    try:
        import os
        
        test_dir = os.path.dirname(os.path.abspath(__file__))
        builder_file = os.path.join(test_dir, 'deer_flow', 'graph', 'builder.py')
        
        with open(builder_file, 'r') as f:
            content = f.read()
        
        node_imports = [
            "debate_orchestrator_node",
            "proponent_node",
            "opponent_node",
            "fact_checker_node",
            "synthesizer_node",
            "moderator_node",
        ]
        
        missing = []
        for node_import in node_imports:
            if node_import not in content:
                missing.append(node_import)
            else:
                print(f"  ✓ {node_import} imported in builder.py")
        
        if missing:
            print(f"✗ Missing node imports: {missing}")
            return False
        
        print("✓ All debate nodes are imported in builder.py")
        return True
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("DEBATE CHAIN IMPLEMENTATION TESTS")
    print("=" * 60)
    
    tests = [
        test_debate_prompts_exist,
        test_debate_agent_llm_map,
        test_debate_nodes_syntax,
        test_debate_nodes_in_files,
        test_debate_nodes_imported_in_builder,
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    print("=" * 60)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
