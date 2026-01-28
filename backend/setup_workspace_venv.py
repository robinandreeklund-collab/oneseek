#!/usr/bin/env python3
"""
Setup script for creating a pre-configured virtual environment for workspace tasks.
This venv includes all necessary testing and development tools.
"""

import os
import subprocess
import sys
from pathlib import Path

def setup_workspace_venv():
    """Create and configure the workspace virtual environment."""
    
    # Determine paths
    script_dir = Path(__file__).parent
    venv_path = script_dir / "deer_flow" / "workspace_venv"
    requirements_file = script_dir / "deer_flow" / "workspace_requirements.txt"
    
    print("=" * 60)
    print("Setting up Workspace Virtual Environment")
    print("=" * 60)
    print(f"Script directory: {script_dir}")
    print(f"Venv path: {venv_path}")
    print(f"Requirements file: {requirements_file}")
    print()
    
    # Check if requirements file exists
    if not requirements_file.exists():
        print(f"❌ Requirements file not found: {requirements_file}")
        print("Please ensure workspace_requirements.txt exists.")
        return False
    
    # Remove old venv if exists
    if venv_path.exists():
        print(f"📁 Removing existing venv at {venv_path}...")
        import shutil
        shutil.rmtree(venv_path)
        print("✓ Old venv removed")
        print()
    
    # Create new venv
    print(f"🔨 Creating new virtual environment...")
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            check=True,
            capture_output=True,
            text=True
        )
        print("✓ Virtual environment created")
        print()
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create venv: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False
    
    # Determine pip path
    if os.name == 'nt':  # Windows
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
    else:  # Unix/Linux/Mac
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    if not pip_path.exists():
        print(f"❌ Pip not found at: {pip_path}")
        return False
    
    # Upgrade pip
    print("📦 Upgrading pip...")
    try:
        subprocess.run(
            [str(python_path), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✓ Pip upgraded")
        print()
    except subprocess.CalledProcessError as e:
        print(f"⚠ Warning: Failed to upgrade pip: {e}")
        print()
    
    # Install requirements
    print(f"📦 Installing requirements from {requirements_file.name}...")
    try:
        result = subprocess.run(
            [str(pip_path), "install", "-r", str(requirements_file)],
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        print("✓ Requirements installed successfully")
        if result.stdout:
            print("\nInstallation output:")
            print(result.stdout[:500])  # First 500 chars
        print()
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Installation timed out after 5 minutes")
        return False
    
    # Verify critical packages
    print("🔍 Verifying installed packages...")
    critical_packages = [
        "pytest", "pylint", "mypy", "black", "flake8", 
        "flask", "requests", "coverage"
    ]
    
    all_verified = True
    for package in critical_packages:
        try:
            result = subprocess.run(
                [str(pip_path), "show", package],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"  ✓ {package}")
        except subprocess.CalledProcessError:
            print(f"  ❌ {package} - NOT FOUND")
            all_verified = False
    
    print()
    
    if not all_verified:
        print("⚠ Warning: Some packages were not installed correctly")
        return False
    
    # Print success message
    print("=" * 60)
    print("✅ Workspace Virtual Environment Setup Complete!")
    print("=" * 60)
    print(f"Venv location: {venv_path}")
    print(f"Python: {python_path}")
    print(f"Pip: {pip_path}")
    print()
    print("Activation commands:")
    if os.name == 'nt':
        print(f"  Windows: {venv_path}\\Scripts\\activate.bat")
        print(f"  PowerShell: {venv_path}\\Scripts\\Activate.ps1")
    else:
        print(f"  Unix/Linux/Mac: source {venv_path}/bin/activate")
    print()
    print("All testing and development tools are pre-installed.")
    print("Agents can now activate this venv and start working immediately!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = setup_workspace_venv()
    sys.exit(0 if success else 1)
