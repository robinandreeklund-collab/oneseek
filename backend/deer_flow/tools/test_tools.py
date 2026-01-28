# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Testing and quality assurance tools for the Tester node in LangGraph.
Provides automated testing, linting, and type checking capabilities.
"""

import logging
import os
import subprocess
import json
from typing import Annotated, Optional, Literal
from pathlib import Path

from langchain_core.tools import tool

from .decorators import log_io

logger = logging.getLogger(__name__)


def _is_python_test_tool_enabled() -> bool:
    """Check if Python test tools are enabled from configuration."""
    env_enabled = os.getenv("ENABLE_PYTHON_TEST_TOOL", "false").lower()
    return env_enabled in ("true", "1", "yes", "on")


def _is_javascript_test_tool_enabled() -> bool:
    """Check if JavaScript test tools are enabled from configuration."""
    env_enabled = os.getenv("ENABLE_JAVASCRIPT_TEST_TOOL", "false").lower()
    return env_enabled in ("true", "1", "yes", "on")


@tool
@log_io
def python_test_tool(
    test_type: Annotated[Literal["pytest", "pylint", "mypy"], "Type of test to run: pytest (unit tests), pylint (linting), mypy (type checking)"],
    path: Annotated[str, "Path to test directory or file to test/check"] = ".",
    verbose: Annotated[bool, "Show detailed output"] = False,
) -> str:
    """
    Run Python tests and quality checks using pytest, pylint, or mypy.
    
    This tool provides automated testing and code quality validation for Python code.
    
    Args:
        test_type: Type of test - "pytest" for unit tests, "pylint" for linting, "mypy" for type checking
        path: Path to the directory or file to test/check
        verbose: Whether to show detailed output
        
    Returns:
        Test results, errors, and quality metrics
    """
    if not _is_python_test_tool_enabled():
        error_msg = "Python test tool is disabled. Set ENABLE_PYTHON_TEST_TOOL=true to enable."
        logger.warning(error_msg)
        return f"Tool disabled: {error_msg}"
    
    logger.info(f"Running Python {test_type} on path: {path}")
    
    try:
        # Build command based on test type
        if test_type == "pytest":
            cmd = ["pytest", path]
            if verbose:
                cmd.append("-v")
            cmd.extend(["--tb=short", "--color=no"])
            
        elif test_type == "pylint":
            cmd = ["pylint", path, "--output-format=text"]
            if not verbose:
                cmd.append("--reports=n")
                
        elif test_type == "mypy":
            cmd = ["mypy", path, "--show-error-codes"]
            if not verbose:
                cmd.append("--no-error-summary")
        else:
            return f"Unknown test type: {test_type}"
        
        # Execute command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minutes timeout
            cwd=os.getcwd()
        )
        
        # Format output
        output = []
        output.append(f"=== {test_type.upper()} Results ===\n")
        
        if result.stdout:
            output.append(result.stdout)
        
        if result.stderr:
            output.append("\nErrors/Warnings:")
            output.append(result.stderr)
        
        # Add result summary
        if result.returncode == 0:
            output.append(f"\n✓ {test_type} completed successfully")
        else:
            output.append(f"\n✗ {test_type} found issues (exit code: {result.returncode})")
        
        return "\n".join(output)
        
    except FileNotFoundError:
        return f"Error: {test_type} is not installed. Install with: pip install {test_type}"
    except subprocess.TimeoutExpired:
        return f"Error: {test_type} timed out after 120 seconds"
    except Exception as e:
        logger.error(f"Error running {test_type}: {e}")
        return f"Error running {test_type}: {str(e)}"


@tool
@log_io
def javascript_test_tool(
    test_type: Annotated[Literal["jest", "vitest", "eslint", "tsc"], "Type of test to run: jest/vitest (unit tests), eslint (linting), tsc (type checking)"],
    path: Annotated[str, "Path to test directory or file to test/check"] = ".",
    project_path: Annotated[Optional[str], "Project root path (for tsc)"] = None,
    verbose: Annotated[bool, "Show detailed output"] = False,
) -> str:
    """
    Run JavaScript/TypeScript tests and quality checks using jest, vitest, eslint, or tsc.
    
    This tool provides automated testing and code quality validation for JavaScript/TypeScript code.
    
    Args:
        test_type: Type of test - "jest"/"vitest" for unit tests, "eslint" for linting, "tsc" for type checking
        path: Path to the directory or file to test/check
        project_path: Project root path (used for tsc to find tsconfig.json)
        verbose: Whether to show detailed output
        
    Returns:
        Test results, errors, and quality metrics
    """
    if not _is_javascript_test_tool_enabled():
        error_msg = "JavaScript test tool is disabled. Set ENABLE_JAVASCRIPT_TEST_TOOL=true to enable."
        logger.warning(error_msg)
        return f"Tool disabled: {error_msg}"
    
    logger.info(f"Running JavaScript {test_type} on path: {path}")
    
    try:
        # Build command based on test type
        if test_type == "jest":
            cmd = ["npx", "jest", path, "--no-coverage"]
            if verbose:
                cmd.append("--verbose")
            cmd.extend(["--colors=false", "--detectOpenHandles"])
            
        elif test_type == "vitest":
            cmd = ["npx", "vitest", "run", path]
            if not verbose:
                cmd.append("--reporter=basic")
                
        elif test_type == "eslint":
            cmd = ["npx", "eslint", path, "--format=stylish"]
            if verbose:
                cmd.append("--debug")
                
        elif test_type == "tsc":
            cmd = ["npx", "tsc", "--noEmit"]
            if project_path:
                cmd.extend(["--project", project_path])
        else:
            return f"Unknown test type: {test_type}"
        
        # Execute command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minutes timeout
            cwd=project_path if project_path and test_type == "tsc" else os.getcwd()
        )
        
        # Format output
        output = []
        output.append(f"=== {test_type.upper()} Results ===\n")
        
        if result.stdout:
            output.append(result.stdout)
        
        if result.stderr:
            output.append("\nErrors/Warnings:")
            output.append(result.stderr)
        
        # Add result summary
        if result.returncode == 0:
            output.append(f"\n✓ {test_type} completed successfully")
        else:
            output.append(f"\n✗ {test_type} found issues (exit code: {result.returncode})")
        
        return "\n".join(output)
        
    except FileNotFoundError:
        return f"Error: {test_type} is not installed. Install with: npm install -D {test_type}"
    except subprocess.TimeoutExpired:
        return f"Error: {test_type} timed out after 120 seconds"
    except Exception as e:
        logger.error(f"Error running {test_type}: {e}")
        return f"Error running {test_type}: {str(e)}"


def get_test_tools():
    """
    Get list of enabled test tools.
    
    Returns:
        List of enabled test tool functions
    """
    tools = []
    
    if _is_python_test_tool_enabled():
        tools.append(python_test_tool)
        logger.info("Python test tool enabled")
    
    if _is_javascript_test_tool_enabled():
        tools.append(javascript_test_tool)
        logger.info("JavaScript test tool enabled")
    
    if not tools:
        logger.warning("No test tools are enabled. Set ENABLE_PYTHON_TEST_TOOL=true or ENABLE_JAVASCRIPT_TEST_TOOL=true")
    
    return tools
