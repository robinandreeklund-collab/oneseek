# Quick Setup Guide: Enable Test Tools

## Required Environment Variables

To use the Code Planner and Tester agents, you **MUST** enable the test tools by setting environment variables.

## Setup Instructions

### Option 1: Copy Example Configuration (Recommended)

```bash
# Navigate to backend directory
cd backend

# Copy the code tools example configuration
cp .env.code_tools_example .env

# The example file already has test tools enabled with:
# ENABLE_PYTHON_TEST_TOOL=true
# ENABLE_JAVASCRIPT_TEST_TOOL=true
```

### Option 2: Add to Existing .env File

```bash
# Navigate to backend directory
cd backend

# Add test tool configuration to your existing .env file
echo "" >> .env
echo "# Test Tools Configuration" >> .env
echo "ENABLE_PYTHON_TEST_TOOL=true" >> .env
echo "ENABLE_JAVASCRIPT_TEST_TOOL=true" >> .env
```

### Option 3: Manual Configuration

1. Open `backend/.env` in your text editor
2. Add these lines:

```bash
# Test Tools Configuration
ENABLE_PYTHON_TEST_TOOL=true
ENABLE_JAVASCRIPT_TEST_TOOL=true
```

## Restart the Server

After adding the environment variables, restart the backend server:

```bash
# Stop the current server (Ctrl+C)

# Start it again
cd backend
python -m uvicorn main:app --reload
```

## Verify Configuration

You can verify the test tools are enabled by checking the logs when the Tester agent runs. You should see:

```
INFO - Tester node using X tools: ['python_repl_tool', 'python_test_tool', 'javascript_test_tool', ...]
```

If test tools are disabled, you'll see warnings:
```
WARNING - Python test tool is disabled. Set ENABLE_PYTHON_TEST_TOOL=true to enable.
```

## What These Variables Do

### ENABLE_PYTHON_TEST_TOOL=true
Enables the Tester agent to:
- Run pytest for unit testing
- Run pylint for code quality checks
- Run mypy for type checking
- Automatically install these tools if missing

### ENABLE_JAVASCRIPT_TEST_TOOL=true
Enables the Tester agent to:
- Run jest/vitest for unit testing
- Run eslint for linting
- Run tsc for TypeScript type checking
- Automatically install these tools if missing

## Troubleshooting

### Issue: Test tools still not working

**Solution 1**: Make sure you restarted the server after adding environment variables

**Solution 2**: Check that the .env file is in the correct location (`backend/.env`)

**Solution 3**: Verify the syntax is correct (no spaces around `=`):
```bash
# Correct
ENABLE_PYTHON_TEST_TOOL=true

# Wrong
ENABLE_PYTHON_TEST_TOOL = true
```

### Issue: "Tool disabled" error in logs

This means the environment variable is not set to `true`. Check:
- Variable name is exactly: `ENABLE_PYTHON_TEST_TOOL` or `ENABLE_JAVASCRIPT_TEST_TOOL`
- Value is exactly: `true` (lowercase)
- File is saved and server restarted

## Complete Example .env File

Here's what your `backend/.env` should look like with test tools enabled:

```bash
# vLLM Configuration
VLLM_URL=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ

# Code Tools
ENABLE_PYTHON_REPL=true
ENABLE_LINUX_SANDBOX=true
ENABLE_FILE_SYSTEM_TOOL=true
ENABLE_REACT_SANDBOX=true

# Test Tools - REQUIRED for Tester agent
ENABLE_PYTHON_TEST_TOOL=true
ENABLE_JAVASCRIPT_TEST_TOOL=true
```

## Next Steps

Once test tools are enabled:

1. ✅ Tester agent can run automated tests
2. ✅ Tester agent will auto-install pytest, pylint, mypy if missing
3. ✅ Tester agent will auto-install jest, eslint, tsc if missing
4. ✅ Code Planner flow works end-to-end with testing phase

See [CODE_PLANNER_CONFIGURATION.md](./CODE_PLANNER_CONFIGURATION.md) for complete usage documentation.
