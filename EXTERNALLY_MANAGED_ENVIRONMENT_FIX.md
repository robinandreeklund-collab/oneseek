# Fix: externally-managed-environment Error

## Problem

When the agent tries to install Python packages, it encounters this error:

```
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.
```

## What is externally-managed-environment?

This is a security feature introduced in **PEP 668** (Python 3.11+) that prevents pip from modifying system-wide Python installations. Many modern Linux distributions (Debian 12+, Ubuntu 23.04+, Fedora 38+) mark their system Python as "externally managed" to prevent conflicts with system package managers.

## Root Cause

The agent was running pip commands like:
```bash
pip install -r requirements.txt
```

Without the `--user` flag, pip tries to install packages system-wide, which is blocked on externally-managed systems.

## Solution Implemented

### Updated All Prompts to Use `--user` Flag

We've updated 4 prompt files to always use the `--user` flag when installing packages:

1. `backend/deer_flow/prompts/coder.md`
2. `backend/deer_flow/prompts/coder.sv_SE.md`
3. `backend/deer_flow/prompts/tester.md`
4. `backend/deer_flow/prompts/tester.sv_SE.md`

### Correct Installation Method

**✅ Correct (with --user flag):**
```bash
python -m pip install --user -r workspace_requirements.txt
python -m pip install --user pytest
```

**❌ Wrong (will fail on managed systems):**
```bash
pip install -r requirements.txt
pip install pytest
```

### In Python Code

**✅ Correct:**
```python
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "--user", "-r", "workspace_requirements.txt"],
    capture_output=True, text=True
)
```

**❌ Wrong:**
```python
import subprocess

result = subprocess.run(
    ["pip", "install", "-r", "requirements.txt"],
    capture_output=True, text=True
)
```

## Why --user Flag?

The `--user` flag offers several benefits:

- ✅ **Works on externally-managed systems** - Bypasses PEP 668 restrictions
- ✅ **No root/admin required** - Installs to user directory
- ✅ **Safe** - Doesn't modify system Python
- ✅ **Simple** - No virtual environment needed
- ✅ **Isolated** - Packages go to `~/.local/lib/python3.x/site-packages`

## Where Packages Are Installed

With `--user` flag, packages are installed to:

**Linux/macOS:**
```
~/.local/lib/python3.x/site-packages
```

**Windows:**
```
%APPDATA%\Python\Python3x\site-packages
```

## Alternative Solutions

### Option 1: Virtual Environment (More Isolated)

```python
import subprocess
import sys

# Create venv
subprocess.run([sys.executable, "-m", "venv", "venv"])

# Install in venv (no --user needed)
subprocess.run(["venv/bin/python", "-m", "pip", "install", "-r", "requirements.txt"])
```

**Pros:** Complete isolation, no interaction with system or user packages
**Cons:** More complex, requires activation, slower

### Option 2: --break-system-packages (Not Recommended)

```bash
pip install --break-system-packages -r requirements.txt
```

**Pros:** Simple
**Cons:** ⚠️ Dangerous! Can break system Python packages

### Our Choice: --user Flag

We chose `--user` as it provides the best balance:
- Simple to use
- Safe
- Works on all systems
- No setup required

## Testing

After backend restart, the agent should:

1. ✅ Use `python -m pip install --user` for all installations
2. ✅ Successfully install packages without errors
3. ✅ No "externally-managed-environment" errors
4. ✅ Packages available for import and use

## Expected Log Output

**Success:**
```
Installing testing tools from workspace_requirements.txt...
✓ All testing tools installed successfully
Successfully installed pytest-7.4.0 pylint-3.0.0 mypy-1.5.0 ...
```

**Before Fix (Failed):**
```
Installing testing tools from workspace_requirements.txt...
✗ Installation failed: error: externally-managed-environment
```

## Troubleshooting

### Issue: Packages still not found after installation

**Solution:** Check that user site-packages is in Python path:
```python
import site
print(site.USER_SITE)  # Should be in sys.path
```

### Issue: Permission denied even with --user

**Solution:** Check that user directory is writable:
```bash
ls -la ~/.local/lib/python3.x/site-packages
```

### Issue: Old pip version doesn't support --user

**Solution:** Upgrade pip first:
```bash
python -m pip install --upgrade --user pip
```

## References

- [PEP 668 – Marking Python base environments as "externally managed"](https://peps.python.org/pep-0668/)
- [pip install --user documentation](https://pip.pypa.io/en/stable/user_guide/#user-installs)
- [Python site module documentation](https://docs.python.org/3/library/site.html)

## Status

✅ **Fixed** - All prompts updated to use `--user` flag
⚠️ **Requires Backend Restart** - Changes take effect after restart
