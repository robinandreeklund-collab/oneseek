# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import sys
from io import StringIO
from typing import Annotated, Optional, Dict, Any

from langchain_core.tools import tool

from .decorators import log_io


def _is_python_repl_enabled() -> bool:
    """Check if Python REPL tool is enabled from configuration."""
    # Check environment variable first
    env_enabled = os.getenv("ENABLE_PYTHON_REPL", "false").lower()
    if env_enabled in ("true", "1", "yes", "on"):
        return True
    return False


class SimplePythonREPL:
    """A simple Python REPL that maintains a persistent namespace.
    
    This implementation fixes the issue where function definitions
    don't work properly by using a single namespace dict for both
    globals and locals in exec().
    """
    
    def __init__(self):
        """Initialize the REPL with a persistent namespace."""
        # Use a single namespace for both globals and locals
        # This ensures function definitions are available when called
        self.namespace: Dict[str, Any] = {
            "__builtins__": __builtins__,
        }
    
    def run(self, code: str) -> str:
        """Execute Python code and return the output.
        
        Args:
            code: Python code to execute
            
        Returns:
            String output from stdout, or empty string if no output
        """
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Execute code with the persistent namespace
            # Using the same dict for both globals and locals ensures
            # function definitions are available when called
            exec(code, self.namespace, self.namespace)
            
            # Get the output
            output = sys.stdout.getvalue()
            return output
            
        finally:
            # Always restore stdout
            sys.stdout = old_stdout


# Initialize REPL with custom implementation
repl: Optional[SimplePythonREPL] = SimplePythonREPL() if _is_python_repl_enabled() else None
logger = logging.getLogger(__name__)


@tool
@log_io
def python_repl_tool(
    code: Annotated[
        str, "The python code to execute to do further analysis or calculation."
    ],
):
    """Use this to execute python code and do data analysis or calculation. If you want to see the output of a value,
    you should print it out with `print(...)`. This is visible to the user."""

    # Check if the tool is enabled
    if not _is_python_repl_enabled():
        error_msg = "Python REPL tool is disabled. Please enable it in environment configuration."
        logger.warning(error_msg)
        return f"Tool disabled: {error_msg}"

    if not isinstance(code, str):
        error_msg = f"Invalid input: code must be a string, got {type(code)}"
        logger.error(error_msg)
        return f"Error executing code:\n```python\n{code}\n```\nError: {error_msg}"

    logger.info("Executing Python code")
    try:
        result = repl.run(code)
        # The SimplePythonREPL returns stdout output directly
        # Empty result means successful execution with no output
        logger.info("Code execution successful")
    except BaseException as e:
        error_msg = repr(e)
        logger.error(error_msg)
        return f"Error executing code:\n```python\n{code}\n```\nError: {error_msg}"

    result_str = f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"
    return result_str
