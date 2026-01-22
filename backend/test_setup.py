"""
Simple test script to validate backend structure and imports
Run this to check if all dependencies are properly installed
"""

def test_imports():
    """Test that all required imports work"""
    print("Testing imports...")
    
    try:
        import fastapi
        print("✓ fastapi")
    except ImportError as e:
        print(f"✗ fastapi: {e}")
    
    try:
        import uvicorn
        print("✓ uvicorn")
    except ImportError as e:
        print(f"✗ uvicorn: {e}")
    
    try:
        import langgraph
        print("✓ langgraph")
    except ImportError as e:
        print(f"✗ langgraph: {e}")
    
    try:
        import langchain
        print("✓ langchain")
    except ImportError as e:
        print(f"✗ langchain: {e}")
    
    try:
        import langchain_community
        print("✓ langchain_community")
    except ImportError as e:
        print(f"✗ langchain_community: {e}")
    
    try:
        import langchain_openai
        print("✓ langchain_openai")
    except ImportError as e:
        print(f"✗ langchain_openai: {e}")
    
    try:
        import vespa
        print("✓ pyvespa")
    except ImportError as e:
        print(f"✗ pyvespa: {e}")
    
    try:
        import sentence_transformers
        print("✓ sentence_transformers")
    except ImportError as e:
        print(f"✗ sentence_transformers: {e}")
    
    try:
        import openai
        print("✓ openai")
    except ImportError as e:
        print(f"✗ openai: {e}")
    
    try:
        import dotenv
        print("✓ python-dotenv")
    except ImportError as e:
        print(f"✗ python-dotenv: {e}")


def test_module_loading():
    """Test that our modules can be loaded"""
    print("\nTesting module loading...")
    
    try:
        import agent
        print("✓ agent.py loads successfully")
    except Exception as e:
        print(f"✗ agent.py: {e}")
    
    try:
        import app
        print("✓ app.py loads successfully")
    except Exception as e:
        print(f"✗ app.py: {e}")
    
    try:
        import deploy_vespa
        print("✓ deploy_vespa.py loads successfully")
    except Exception as e:
        print(f"✗ deploy_vespa.py: {e}")


def test_env_file():
    """Check if .env or .env.example exists"""
    import os
    
    print("\nChecking environment configuration...")
    
    if os.path.exists(".env"):
        print("✓ .env file exists")
        
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = ["VLLM_URL", "VLLM_MODEL"]
        for var in required_vars:
            if os.getenv(var):
                print(f"  ✓ {var} is set")
            else:
                print(f"  ⚠ {var} is not set")
        
        optional_vars = ["VESPA_URL", "VESPA_CERT_PATH", "VESPA_KEY_PATH"]
        for var in optional_vars:
            if os.getenv(var):
                print(f"  ✓ {var} is set")
            else:
                print(f"  ⚠ {var} is not set (optional - needed for Vespa)")
    
    elif os.path.exists(".env.example"):
        print("⚠ .env.example exists but .env does not")
        print("  Run: cp .env.example .env")
    else:
        print("✗ No .env or .env.example file found")


if __name__ == "__main__":
    print("="*60)
    print("OneSeek Backend Test Suite")
    print("="*60)
    
    test_imports()
    test_module_loading()
    test_env_file()
    
    print("\n" + "="*60)
    print("Test complete!")
    print("="*60)
