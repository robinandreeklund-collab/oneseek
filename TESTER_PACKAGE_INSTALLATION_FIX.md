# Tester Package Installation Fix - Summary

## Problem

When the tester agent tried to run tests, it encountered errors because required testing tools (pytest, pylint, mypy for Python; jest, eslint, tsc for JavaScript) were not installed in the development environment.

### User-Reported Issues

From the problem statement:
> "Problemet med pytest - Det verkar som att pytest inte är installerat i vår miljö"
> "Problemet med pylint och mypy - Det verkar som att både pylint och mypy saknas"
> "modellen skapade en venv miljö. men ser inte ut som den försökte installera dom"

The tester created a virtual environment but didn't install the required packages before trying to use them.

### Root Cause

The tester prompts (`tester.md` and `tester.sv_SE.md`) didn't include instructions for:
1. Checking if required testing tools are installed
2. Installing missing tools before running tests
3. Using python_repl_tool to perform installations

## Solution

Updated both tester prompts to add comprehensive package installation instructions that the agent will follow before running any tests.

### Key Changes

#### 1. Added "Package Installation and Environment Setup" Section

**Location**: After "Testing Philosophy", before "Testing Process"

This new section includes:
- **CRITICAL** instruction emphasizing the importance of checking tools first
- Step-by-step guides for checking and installing Python tools
- Step-by-step guides for checking and installing JavaScript tools
- Complete, copy-paste ready Python code for installations
- Installation guidelines and best practices

#### 2. Added Step 0 to Testing Process

**New first step**: "Check and Install Required Tools (FIRST STEP)"

Before the agent does anything else, it must:
1. Check if required testing tools are installed
2. Use python_repl_tool to verify installation
3. Install missing tools if needed
4. Report installation status to the user

#### 3. Updated Important Guidelines

Added two new priority guidelines:
1. **Check for tool installation FIRST** - Always verify before running tests
2. **Install missing tools automatically** - Use python_repl_tool for installations

#### 4. Added New Edge Case

**"Testing Tools Not Installed"** - Shows expected behavior when tools are missing:
```
⚠ Testing tools not found. Installing required packages...

Installing: pytest, pylint, mypy
✓ Successfully installed testing tools

Proceeding with test execution...
```

## How It Works

### For Python Testing

**Step 1: Check Installation**
```python
import subprocess
import sys

def check_package_installed(package_name):
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "show", package_name], 
                               capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

print(f"pytest installed: {check_package_installed('pytest')}")
print(f"pylint installed: {check_package_installed('pylint')}")
print(f"mypy installed: {check_package_installed('mypy')}")
```

**Step 2: Install Missing Tools**
```python
import subprocess
import sys

packages = ['pytest', 'pylint', 'mypy']
missing = []

for pkg in packages:
    result = subprocess.run([sys.executable, "-m", "pip", "show", pkg], 
                           capture_output=True, text=True)
    if result.returncode != 0:
        missing.append(pkg)

if missing:
    print(f"Installing missing packages: {', '.join(missing)}")
    result = subprocess.run([sys.executable, "-m", "pip", "install"] + missing, 
                           capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ Successfully installed: {', '.join(missing)}")
    else:
        print(f"✗ Installation failed: {result.stderr}")
else:
    print("✓ All required Python testing tools are already installed")
```

### For JavaScript Testing

**Step 1: Check Installation**
```python
import subprocess
import os

def check_npm_package(package_name):
    try:
        result = subprocess.run(["npm", "list", package_name], 
                               capture_output=True, text=True, cwd=os.getcwd())
        return package_name in result.stdout
    except:
        return False

print(f"jest installed: {check_npm_package('jest')}")
print(f"eslint installed: {check_npm_package('eslint')}")
print(f"typescript installed: {check_npm_package('typescript')}")
```

**Step 2: Install Missing Tools**
```python
import subprocess
import os

packages = [('jest', 'jest'), ('eslint', 'eslint'), ('typescript', 'typescript')]
missing = []

for pkg_name, npm_name in packages:
    result = subprocess.run(["npm", "list", pkg_name], 
                           capture_output=True, text=True, cwd=os.getcwd())
    if pkg_name not in result.stdout:
        missing.append(npm_name)

if missing:
    print(f"Installing missing packages: {', '.join(missing)}")
    result = subprocess.run(["npm", "install", "-D"] + missing, 
                           capture_output=True, text=True, cwd=os.getcwd())
    if result.returncode == 0:
        print(f"✓ Successfully installed: {', '.join(missing)}")
    else:
        print(f"✗ Installation failed: {result.stderr}")
else:
    print("✓ All required JavaScript testing tools are already installed")
```

## Key Features

### 1. Automatic Detection
The agent automatically checks if tools are installed before attempting to use them.

### 2. Automatic Installation
If tools are missing, the agent installs them without manual intervention.

### 3. Environment Isolation
Uses `python_repl_tool` which respects virtual environments:
- If code uses a venv, installations happen within that venv
- Proper environment isolation maintained

### 4. Batch Installation
Installs all missing tools at once rather than one-by-one (more efficient).

### 5. Clear Reporting
Reports installation status clearly:
- What's being installed
- Success or failure
- Error messages if something goes wrong

### 6. Graceful Error Handling
If installation fails, the agent reports the error clearly rather than failing silently.

### 7. Bilingual Support
Complete instructions in both English and Swedish.

## Expected Behavior

### Scenario 1: No Tools Installed (Clean Environment)

**Agent Output:**
```
Checking for required testing tools...

pytest installed: False
pylint installed: False
mypy installed: False

Installing missing packages: pytest, pylint, mypy
✓ Successfully installed: pytest, pylint, mypy

Proceeding with test execution...
```

### Scenario 2: Some Tools Missing

**Agent Output:**
```
Checking for required testing tools...

pytest installed: True
pylint installed: False
mypy installed: True

Installing missing packages: pylint
✓ Successfully installed: pylint

Proceeding with test execution...
```

### Scenario 3: All Tools Installed

**Agent Output:**
```
Checking for required testing tools...

pytest installed: True
pylint installed: True
mypy installed: True

✓ All required Python testing tools are already installed

Running tests...
```

### Scenario 4: Installation Failure

**Agent Output:**
```
Checking for required testing tools...

Installing missing packages: pytest, pylint, mypy
✗ Installation failed: Permission denied

Unable to install testing tools. Please install manually:
pip install pytest pylint mypy
```

## Installation Guidelines

The agent now follows these guidelines:

1. **Always check before installing**: Don't assume tools are missing
2. **Install all required tools at once**: More efficient than one-by-one
3. **Use python_repl_tool for installations**: Provides proper environment isolation
4. **Report installation status**: Keep user informed
5. **Handle failures gracefully**: Clear error messages
6. **Virtual environments**: Automatic detection and usage

## Files Changed

1. **backend/deer_flow/prompts/tester.md** (+130 lines)
   - Added "Package Installation and Environment Setup" section
   - Updated "Testing Process" with Step 0
   - Updated "Important Guidelines"
   - Added "Testing Tools Not Installed" edge case

2. **backend/deer_flow/prompts/tester.sv_SE.md** (+130 lines)
   - Swedish translation of all English changes
   - Maintains consistency between languages

## Testing Recommendations

To verify the fix works correctly:

### Test 1: Clean Environment
1. Create a new venv without pytest/pylint/mypy
2. Ask tester to validate Python code
3. Verify agent installs missing tools
4. Confirm tests run successfully

### Test 2: Partial Installation
1. Install only pytest (leave pylint and mypy missing)
2. Ask tester to validate Python code
3. Verify agent detects pytest exists
4. Verify agent installs only missing tools

### Test 3: Complete Installation
1. Install all tools (pytest, pylint, mypy)
2. Ask tester to validate Python code
3. Verify agent confirms tools are installed
4. Verify agent proceeds directly to testing

### Test 4: JavaScript Testing
1. Create JavaScript project without jest/eslint/tsc
2. Ask tester to validate JavaScript code
3. Verify agent installs missing tools via npm
4. Confirm tests run successfully

### Test 5: Error Handling
1. Simulate installation failure (e.g., no internet)
2. Verify agent reports error clearly
3. Confirm agent suggests manual installation

## Impact

### Before
- ❌ Agent tried to run tests without checking for tools
- ❌ Tests failed with "command not found" errors
- ❌ User had to manually install tools
- ❌ Workflow interrupted

### After
- ✅ Agent checks for tools before testing
- ✅ Agent automatically installs missing tools
- ✅ Tests run smoothly without manual intervention
- ✅ Clear status reporting throughout
- ✅ Works with virtual environments

## Related Issues

This fix addresses the user's request:
> "Kan vi även promta modellen att det får installera vad den vill för att kunna använda de verktyg och tester den vill utföra? t.ex kolla din befintliga utveckingsmiljö om den innehåller de tänka paketet. om inte istallerar du dom direkt. som t.ex pylint och mypy"

The agent now:
- ✅ Checks the development environment
- ✅ Detects missing packages
- ✅ Installs them directly
- ✅ Works with pytest, pylint, mypy, and JavaScript tools

## Related Documentation

- [CODE_PLANNER_ARCHITECTURE.md](./CODE_PLANNER_ARCHITECTURE.md) - Overall architecture
- [IMPLEMENTATION_COMPLETE.md](./IMPLEMENTATION_COMPLETE.md) - Implementation summary
- [tester.md](./backend/deer_flow/prompts/tester.md) - Updated English prompt
- [tester.sv_SE.md](./backend/deer_flow/prompts/tester.sv_SE.md) - Updated Swedish prompt

---

**Date**: 2026-01-28
**Issue**: Tester fails because pytest, pylint, mypy not installed
**Status**: ✅ FIXED
**Commit**: Add package installation instructions to tester prompts
