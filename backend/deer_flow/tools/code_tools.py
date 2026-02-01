# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Code-related tools for the Coder node in LangGraph.
Provides Linux sandbox, file system management, and React preview capabilities.
"""

import contextvars
import logging
import os
import subprocess
import tempfile
import json
import threading
from typing import Annotated, Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from langchain_core.tools import tool

from .decorators import log_io

logger = logging.getLogger(__name__)

# Run-scoped storage for tracking workspace files
# Using a simple global dict with automatic run_id generation
_workspace_files_by_run: Dict[str, List[Dict[str, Any]]] = {}
_workspace_files_lock = threading.Lock()
_current_run_id: Dict[int, str] = {}  # Maps thread_id to run_id
_run_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "workspace_run_id",
    default=None,
)

_workspace_history_by_run: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
_workspace_history_lock = threading.Lock()
_WORKSPACE_HISTORY_MAX_ENTRIES = int(
    os.getenv("WORKSPACE_HISTORY_MAX_ENTRIES", "50")
)
_WORKSPACE_HISTORY_MAX_CONTENT_BYTES = int(
    os.getenv("WORKSPACE_HISTORY_MAX_CONTENT_BYTES", "1000000")
)


def get_workspace_root() -> Path:
    """Get or initialize the workspace root directory."""
    code_workspace = os.getenv("CODE_WORKSPACE_ROOT", None)
    if code_workspace:
        workspace_root = Path(code_workspace)
    else:
        workspace_root = Path(tempfile.gettempdir()) / "oneseek_workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    return workspace_root


def _resolve_workspace_path(path: str, workspace_root: Path) -> Path:
    target_path = (workspace_root / path).resolve()
    if not str(target_path).startswith(str(workspace_root)):
        raise ValueError(f"Security error: Path '{path}' is outside workspace")
    return target_path


def _read_file_content_if_small(target_path: Path) -> tuple[Optional[str], int]:
    try:
        file_size = target_path.stat().st_size
    except OSError:
        return None, 0
    if file_size > _WORKSPACE_HISTORY_MAX_CONTENT_BYTES:
        return None, file_size
    try:
        return target_path.read_text(encoding="utf-8", errors="replace"), file_size
    except OSError:
        return None, file_size


def _init_workspace_history(run_id: str) -> Dict[str, List[Dict[str, Any]]]:
    if run_id not in _workspace_history_by_run:
        _workspace_history_by_run[run_id] = {"undo": [], "redo": []}
    return _workspace_history_by_run[run_id]


def record_workspace_change(run_id: str, entry: Dict[str, Any]):
    """Record a workspace change for undo/redo."""
    with _workspace_history_lock:
        history = _init_workspace_history(run_id)
        history["undo"].append(entry)
        history["redo"].clear()
        if len(history["undo"]) > _WORKSPACE_HISTORY_MAX_ENTRIES:
            history["undo"] = history["undo"][-_WORKSPACE_HISTORY_MAX_ENTRIES:]


def get_workspace_history_counts(run_id: str) -> Dict[str, int]:
    with _workspace_history_lock:
        history = _init_workspace_history(run_id)
        return {
            "undo_count": len(history["undo"]),
            "redo_count": len(history["redo"]),
        }


def _apply_workspace_change(
    target_path: Path,
    entry: Dict[str, Any],
    apply_after: bool,
) -> tuple[bool, str]:
    operation = entry.get("operation")
    before_content = entry.get("before_content")
    after_content = entry.get("after_content")
    is_dir = entry.get("is_dir", False)
    before_exists = entry.get("before_exists", False)
    after_exists = entry.get("after_exists", False)

    if apply_after:
        content = after_content
        exists = after_exists
        operation_label = operation
    else:
        content = before_content
        exists = before_exists
        operation_label = operation

    if operation_label in ("created", "modified"):
        if not exists and not apply_after:
            if target_path.exists():
                target_path.unlink()
            return True, "deleted"
        if content is None:
            return False, "Missing content snapshot for restore"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return True, "restored" if not apply_after else "modified"
    if operation_label == "deleted":
        if apply_after:
            if target_path.exists():
                target_path.unlink()
            return True, "deleted"
        if content is None:
            return False, "Missing content snapshot for restore"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return True, "restored"
    if operation_label == "created_dir":
        if apply_after:
            target_path.mkdir(parents=True, exist_ok=True)
            return True, "created_dir"
        if target_path.exists():
            import shutil
            shutil.rmtree(target_path)
        return True, "deleted_dir"
    if operation_label == "deleted_dir":
        if apply_after:
            if target_path.exists():
                import shutil
                shutil.rmtree(target_path)
            return True, "deleted_dir"
        target_path.mkdir(parents=True, exist_ok=True)
        return True, "created_dir"

    return False, f"Unsupported operation: {operation_label}"


def undo_workspace_change(run_id: str) -> Dict[str, Any]:
    with _workspace_history_lock:
        history = _init_workspace_history(run_id)
        if not history["undo"]:
            return {"status": "empty"}
        entry = history["undo"].pop()

    workspace_root = get_workspace_root()
    try:
        target_path = _resolve_workspace_path(entry["path"], workspace_root)
    except ValueError as exc:
        with _workspace_history_lock:
            history = _init_workspace_history(run_id)
            history["undo"].append(entry)
        return {"status": "error", "message": str(exc)}

    try:
        success, applied_operation = _apply_workspace_change(
            target_path, entry, apply_after=False
        )
    except Exception as exc:  # noqa: BLE001
        with _workspace_history_lock:
            history = _init_workspace_history(run_id)
            history["undo"].append(entry)
        return {"status": "error", "message": str(exc)}

    if not success:
        with _workspace_history_lock:
            history = _init_workspace_history(run_id)
            history["undo"].append(entry)
        return {"status": "error", "message": applied_operation}

    with _workspace_history_lock:
        history = _init_workspace_history(run_id)
        history["redo"].append(entry)
        if len(history["redo"]) > _WORKSPACE_HISTORY_MAX_ENTRIES:
            history["redo"] = history["redo"][-_WORKSPACE_HISTORY_MAX_ENTRIES:]

    try:
        file_size = target_path.stat().st_size if target_path.exists() else 0
    except OSError:
        file_size = 0
    track_workspace_file(
        entry["path"],
        f"undo:{applied_operation}",
        file_size,
        None,
        run_id=run_id,
    )
    return {"status": "success", "entry": entry, "operation": applied_operation}


def redo_workspace_change(run_id: str) -> Dict[str, Any]:
    with _workspace_history_lock:
        history = _init_workspace_history(run_id)
        if not history["redo"]:
            return {"status": "empty"}
        entry = history["redo"].pop()

    workspace_root = get_workspace_root()
    try:
        target_path = _resolve_workspace_path(entry["path"], workspace_root)
    except ValueError as exc:
        with _workspace_history_lock:
            history = _init_workspace_history(run_id)
            history["redo"].append(entry)
        return {"status": "error", "message": str(exc)}

    try:
        success, applied_operation = _apply_workspace_change(
            target_path, entry, apply_after=True
        )
    except Exception as exc:  # noqa: BLE001
        with _workspace_history_lock:
            history = _init_workspace_history(run_id)
            history["redo"].append(entry)
        return {"status": "error", "message": str(exc)}

    if not success:
        with _workspace_history_lock:
            history = _init_workspace_history(run_id)
            history["redo"].append(entry)
        return {"status": "error", "message": applied_operation}

    with _workspace_history_lock:
        history = _init_workspace_history(run_id)
        history["undo"].append(entry)
        if len(history["undo"]) > _WORKSPACE_HISTORY_MAX_ENTRIES:
            history["undo"] = history["undo"][-_WORKSPACE_HISTORY_MAX_ENTRIES:]

    try:
        file_size = target_path.stat().st_size if target_path.exists() else 0
    except OSError:
        file_size = 0
    track_workspace_file(
        entry["path"],
        f"redo:{applied_operation}",
        file_size,
        None,
        run_id=run_id,
    )
    return {"status": "success", "entry": entry, "operation": applied_operation}


def list_workspace_files(
    run_id: Optional[str] = None,
    max_files: int = 1000,
) -> List[Dict[str, Any]]:
    workspace_root = get_workspace_root()
    files: List[Dict[str, Any]] = []
    count = 0
    for path in sorted(workspace_root.rglob("*")):
        if count >= max_files:
            break
        if path.is_dir():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        relative_path = path.relative_to(workspace_root).as_posix()
        files.append(
            {
                "path": relative_path,
                "name": path.name,
                "size": stat.st_size,
                "operation": "existing",
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )
        count += 1
    return files


def get_workspace_file_content(path: str, run_id: Optional[str] = None) -> Dict[str, Any]:
    workspace_root = get_workspace_root()
    target_path = _resolve_workspace_path(path, workspace_root)
    if not target_path.exists() or not target_path.is_file():
        return {"status": "missing"}
    content, size = _read_file_content_if_small(target_path)
    return {
        "status": "ok",
        "content": content or "",
        "truncated": content is None and size > 0,
        "size": size,
    }


def get_latest_workspace_diff(run_id: str, path: str) -> Dict[str, Any]:
    with _workspace_history_lock:
        history = _init_workspace_history(run_id)
        candidates = list(reversed(history["undo"])) + list(reversed(history["redo"]))
    for entry in candidates:
        if entry.get("path") == path:
            before = entry.get("before_content")
            after = entry.get("after_content")
            return {
                "status": "ok",
                "before": before,
                "after": after,
                "before_truncated": entry.get("before_truncated", False),
                "after_truncated": entry.get("after_truncated", False),
                "before_exists": entry.get("before_exists", False),
                "after_exists": entry.get("after_exists", False),
                "operation": entry.get("operation"),
            }
    return {"status": "missing"}


def set_current_run_id(run_id: str):
    """Set the current run_id for this thread."""
    _run_id_var.set(run_id)
    thread_id = threading.get_ident()
    _current_run_id[thread_id] = run_id
    logger.info(f"Set run_id={run_id} for thread={thread_id}")


def get_current_run_id() -> str:
    """Get the current run_id for this thread, or 'default' if not set."""
    run_id = _run_id_var.get()
    if run_id:
        return run_id
    thread_id = threading.get_ident()
    return _current_run_id.get(thread_id, "default")


def get_workspace_files(run_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get the list of workspace files tracked for the given run."""
    if run_id is None:
        run_id = get_current_run_id()
    
    with _workspace_files_lock:
        files = _workspace_files_by_run.get(run_id, [])
        logger.info(f"Retrieved {len(files)} workspace files for run_id={run_id}")
        return files.copy()  # Return copy to avoid external modifications


def clear_workspace_files(run_id: Optional[str] = None):
    """Clear the workspace files for the given run."""
    if run_id is None:
        run_id = get_current_run_id()
    
    with _workspace_files_lock:
        if run_id in _workspace_files_by_run:
            del _workspace_files_by_run[run_id]
        logger.info(f"Cleared workspace files for run_id={run_id}")


def track_workspace_file(path: str, operation: str, size: int = 0, content: Optional[str] = None, run_id: Optional[str] = None):
    """Track a file operation in the workspace context for the given run."""
    if run_id is None:
        run_id = get_current_run_id()
    
    with _workspace_files_lock:
        if run_id not in _workspace_files_by_run:
            _workspace_files_by_run[run_id] = []
        
        files = _workspace_files_by_run[run_id]
        
        # Find existing entry for this path
        existing = next((f for f in files if f['path'] == path), None)
        
        file_info = {
            'path': path,
            'name': os.path.basename(path),
            'size': size,
            'operation': operation,
            'modified': datetime.now().isoformat()
        }
        
        # Only include first 1000 chars of content to avoid huge payloads
        if content and operation == 'write':
            file_info['content'] = content[:1000] if len(content) > 1000 else content
            file_info['truncated'] = len(content) > 1000
        
        if existing:
            # Update existing entry
            existing.update(file_info)
            logger.info(f"[run_id={run_id}] Updated workspace file: {path}, operation: {operation}")
        else:
            # Add new entry
            files.append(file_info)
            logger.info(f"[run_id={run_id}] Tracking workspace file: {path}, operation: {operation}")
        
        logger.info(f"[run_id={run_id}] Current workspace files count: {len(files)}")


def _is_linux_sandbox_enabled() -> bool:
    """Check if Linux sandbox tool is enabled from configuration."""
    env_enabled = os.getenv("ENABLE_LINUX_SANDBOX", "false").lower()
    return env_enabled in ("true", "1", "yes", "on")


def _is_file_system_tool_enabled() -> bool:
    """Check if file system tool is enabled from configuration."""
    env_enabled = os.getenv("ENABLE_FILE_SYSTEM_TOOL", "false").lower()
    return env_enabled in ("true", "1", "yes", "on")


def _is_react_sandbox_enabled() -> bool:
    """Check if React sandbox tool is enabled from configuration."""
    env_enabled = os.getenv("ENABLE_REACT_SANDBOX", "false").lower()
    return env_enabled in ("true", "1", "yes", "on")


def ensure_workspace_requirements() -> str:
    """
    Ensure workspace_requirements.txt exists in the workspace root.
    This file contains all Python testing and development tools.
    Returns the path to the requirements file.
    """
    # Get workspace root - use CODE_WORKSPACE_ROOT directly (no extra subdirectory)
    # Only add 'oneseek_workspace' if using temp directory (fallback)
    workspace_root = get_workspace_root()
    
    requirements_path = workspace_root / "workspace_requirements.txt"
    
    # Content for workspace requirements
    requirements_content = """# OneSeek Workspace Requirements
# This file contains all Python testing and development tools needed for the workspace
# Install with: pip install -r workspace_requirements.txt

# Testing Framework
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.1

# Code Quality & Linting
pylint>=3.0.0
flake8>=6.1.0
black>=23.7.0
isort>=5.12.0

# Type Checking
mypy>=1.5.0

# Code Coverage
coverage>=7.3.0

# Common Development Dependencies
requests>=2.31.0
python-dotenv>=1.0.0
"""
    
    # Create or update the requirements file if it doesn't exist
    if not requirements_path.exists():
        requirements_path.write_text(requirements_content, encoding='utf-8')
        logger.info(f"Created workspace_requirements.txt at {requirements_path}")
    
    return str(requirements_path)


@tool
@log_io
def linux_sandbox_tool(
    command: Annotated[str, "The Linux command to execute in the sandbox environment."],
    working_dir: Annotated[Optional[str], "Optional working directory for command execution."] = None,
) -> str:
    """
    Execute Linux commands in an isolated sandbox environment using WSL or Docker.
    
    This tool provides a secure, isolated environment for running shell commands,
    compiling code, or testing applications without affecting the host system.
    
    Args:
        command: The shell command to execute
        working_dir: Optional working directory path
        
    Returns:
        Command output or error message
    """
    if not _is_linux_sandbox_enabled():
        error_msg = "Linux sandbox tool is disabled. Set ENABLE_LINUX_SANDBOX=true to enable."
        logger.warning(error_msg)
        return f"Tool disabled: {error_msg}"
    
    # Ensure workspace_requirements.txt exists
    ensure_workspace_requirements()
    
    logger.info(f"Executing command in Linux sandbox: {command}")
    
    try:
        # Check if WSL is available
        wsl_check = subprocess.run(
            ["wsl", "--status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        use_wsl = wsl_check.returncode == 0
        
        if use_wsl:
            # Execute in WSL
            wsl_command = f"cd {working_dir or '/tmp'} && {command}"
            result = subprocess.run(
                ["wsl", "bash", "-c", wsl_command],
                capture_output=True,
                text=True,
                timeout=30
            )
        else:
            # Fallback to Docker if WSL not available
            docker_image = os.getenv("DOCKER_SANDBOX_IMAGE", "ubuntu:latest")
            docker_cmd = [
                "docker", "run", "--rm",
                "-w", working_dir or "/workspace",
                docker_image,
                "bash", "-c", command
            ]
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
        
        if result.returncode == 0:
            logger.info("Command executed successfully in sandbox")
            return f"✓ Command executed successfully:\n\n```bash\n{command}\n```\n\nOutput:\n```\n{result.stdout}\n```"
        else:
            logger.error(f"Command failed with exit code {result.returncode}")
            return f"✗ Command failed:\n\n```bash\n{command}\n```\n\nError (exit code {result.returncode}):\n```\n{result.stderr}\n```"
            
    except subprocess.TimeoutExpired:
        error_msg = f"Command timed out after 30 seconds"
        logger.error(error_msg)
        return f"✗ {error_msg}:\n```bash\n{command}\n```"
    except FileNotFoundError as e:
        error_msg = f"WSL or Docker not found. Please install WSL or Docker to use this tool."
        logger.error(error_msg)
        return f"✗ {error_msg}"
    except Exception as e:
        error_msg = f"Error executing command: {repr(e)}"
        logger.error(error_msg)
        return f"✗ {error_msg}:\n```bash\n{command}\n```"


@tool
@log_io
def file_system_tool(
    operation: Annotated[str, "Operation to perform: 'read', 'write', 'list', 'delete', or 'create_dir'"],
    path: Annotated[str, "File or directory path (relative to workspace)"],
    content: Annotated[Optional[str], "Content to write (for 'write' operation)"] = None,
) -> str:
    """
    Manage files and directories in the WSL/sandbox workspace.
    
    Allows the agent to read, write, list, and manage files needed for code development.
    All operations are scoped to a safe workspace directory.
    
    Args:
        operation: The file system operation to perform
        path: Target file or directory path
        content: Content for write operations
        
    Returns:
        Operation result or error message
    """
    if not _is_file_system_tool_enabled():
        error_msg = "File system tool is disabled. Set ENABLE_FILE_SYSTEM_TOOL=true to enable."
        logger.warning(error_msg)
        return f"Tool disabled: {error_msg}"
    
    # Get workspace root - use CODE_WORKSPACE_ROOT directly (no extra subdirectory)
    # Only add 'oneseek_workspace' if using temp directory (fallback)
    workspace_root = get_workspace_root()
    
    # Ensure workspace_requirements.txt exists in workspace
    ensure_workspace_requirements()
    
    # Resolve and validate path
    try:
        target_path = _resolve_workspace_path(path, workspace_root)
        
        logger.info(f"File system operation: {operation} on {target_path}")
        
        if operation == "read":
            if not target_path.exists():
                return f"✗ File not found: {path}"
            if not target_path.is_file():
                return f"✗ Not a file: {path}"
            
            content = target_path.read_text(encoding='utf-8')
            return f"✓ File content of '{path}':\n\n```\n{content}\n```"
        
        elif operation == "write":
            if content is None:
                return f"✗ No content provided for write operation"
            
            existed = target_path.exists()
            before_content = None
            before_size = 0
            before_truncated = False
            if existed and target_path.is_file():
                before_content, before_size = _read_file_content_if_small(target_path)
                before_truncated = (
                    before_content is None
                    and before_size > _WORKSPACE_HISTORY_MAX_CONTENT_BYTES
                )
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding='utf-8')
            
            # Track this file operation
            file_size = len(content.encode('utf-8'))
            operation_label = "created" if not existed else "modified"
            track_workspace_file(path, operation_label, file_size, content)

            after_truncated = file_size > _WORKSPACE_HISTORY_MAX_CONTENT_BYTES
            after_content = content if not after_truncated else None
            record_workspace_change(
                get_current_run_id(),
                {
                    "path": path,
                    "operation": operation_label,
                    "before_content": before_content,
                    "after_content": after_content,
                    "before_truncated": before_truncated,
                    "after_truncated": after_truncated,
                    "before_exists": existed,
                    "after_exists": True,
                    "is_dir": False,
                    "before_size": before_size,
                    "after_size": file_size,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            
            return f"✓ Successfully wrote {len(content)} bytes to '{path}'"
        
        elif operation == "list":
            if not target_path.exists():
                return f"✗ Directory not found: {path}"
            if not target_path.is_dir():
                return f"✗ Not a directory: {path}"
            
            items = []
            for item in sorted(target_path.iterdir()):
                item_type = "📁" if item.is_dir() else "📄"
                items.append(f"{item_type} {item.name}")
            
            return f"✓ Contents of '{path}':\n\n" + "\n".join(items) if items else "✓ Directory is empty"
        
        elif operation == "delete":
            if not target_path.exists():
                return f"✗ Path not found: {path}"
            
            if target_path.is_file():
                before_content, before_size = _read_file_content_if_small(target_path)
                before_truncated = (
                    before_content is None
                    and before_size > _WORKSPACE_HISTORY_MAX_CONTENT_BYTES
                )
                try:
                    file_size = target_path.stat().st_size
                except OSError:
                    file_size = 0
                track_workspace_file(path, "deleted", file_size)
                record_workspace_change(
                    get_current_run_id(),
                    {
                        "path": path,
                        "operation": "deleted",
                        "before_content": before_content,
                        "after_content": None,
                        "before_truncated": before_truncated,
                        "after_truncated": False,
                        "before_exists": True,
                        "after_exists": False,
                        "is_dir": False,
                        "before_size": before_size,
                        "after_size": 0,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
                target_path.unlink()
                return f"✓ Deleted file: {path}"
            elif target_path.is_dir():
                import shutil
                track_workspace_file(path, "deleted_dir", 0)
                record_workspace_change(
                    get_current_run_id(),
                    {
                        "path": path,
                        "operation": "deleted_dir",
                        "before_content": None,
                        "after_content": None,
                        "before_truncated": False,
                        "after_truncated": False,
                        "before_exists": True,
                        "after_exists": False,
                        "is_dir": True,
                        "before_size": 0,
                        "after_size": 0,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
                shutil.rmtree(target_path)
                return f"✓ Deleted directory: {path}"
        
        elif operation == "create_dir":
            existed = target_path.exists()
            target_path.mkdir(parents=True, exist_ok=True)
            track_workspace_file(path, "created_dir", 0)
            record_workspace_change(
                get_current_run_id(),
                {
                    "path": path,
                    "operation": "created_dir",
                    "before_content": None,
                    "after_content": None,
                    "before_truncated": False,
                    "after_truncated": False,
                    "before_exists": existed,
                    "after_exists": True,
                    "is_dir": True,
                    "before_size": 0,
                    "after_size": 0,
                    "timestamp": datetime.now().isoformat(),
                },
            )
            return f"✓ Created directory: {path}"
        
        else:
            return f"✗ Unknown operation: {operation}. Valid operations: read, write, list, delete, create_dir"
    
    except Exception as e:
        error_msg = f"Error performing {operation} on '{path}': {repr(e)}"
        logger.error(error_msg)
        return f"✗ {error_msg}"


@tool
@log_io
def react_sandbox_tool(
    action: Annotated[str, "Action to perform: 'create', 'update', 'preview', or 'stop'"],
    project_name: Annotated[str, "Name of the React/Next.js project"],
    files: Annotated[Optional[Dict[str, str]], "Dictionary of filename to content for create/update"] = None,
    port: Annotated[Optional[int], "Port number for preview server (default: 3001)"] = None,
) -> str:
    """
    Manage live React/Next.js sandbox environments with real-time preview.
    
    Create, update, and preview React applications with live code changes.
    The preview integrates with the frontend for real-time display.
    
    Args:
        action: The sandbox action to perform
        project_name: Name/identifier for the project
        files: Files to create or update (for create/update actions)
        port: Port for development server (default: 3001)
        
    Returns:
        Action result with preview URL or error message
    """
    if not _is_react_sandbox_enabled():
        error_msg = "React sandbox tool is disabled. Set ENABLE_REACT_SANDBOX=true to enable."
        logger.warning(error_msg)
        return f"Tool disabled: {error_msg}"
    
    if port is None:
        port = 3001
    
    # Get sandbox root directory
    sandbox_root = Path(os.getenv("REACT_SANDBOX_ROOT", tempfile.gettempdir())) / "oneseek_react_sandboxes"
    sandbox_root.mkdir(parents=True, exist_ok=True)
    
    project_dir = sandbox_root / project_name
    
    logger.info(f"React sandbox action: {action} for project '{project_name}'")
    
    try:
        if action == "create":
            if project_dir.exists():
                return f"✗ Project '{project_name}' already exists. Use 'update' to modify."
            
            # Create Next.js project structure
            project_dir.mkdir(parents=True)
            
            # Create basic Next.js structure
            (project_dir / "src").mkdir(exist_ok=True)
            (project_dir / "src" / "app").mkdir(exist_ok=True)
            (project_dir / "public").mkdir(exist_ok=True)
            
            # Create package.json
            package_json = {
                "name": project_name,
                "version": "0.1.0",
                "private": True,
                "scripts": {
                    "dev": f"next dev -p {port}",
                    "build": "next build",
                    "start": "next start"
                },
                "dependencies": {
                    "next": "^14.0.0",
                    "react": "^18.0.0",
                    "react-dom": "^18.0.0"
                }
            }
            (project_dir / "package.json").write_text(json.dumps(package_json, indent=2))
            
            # Create files if provided
            if files:
                for filename, content in files.items():
                    file_path = project_dir / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding='utf-8')
            
            return f"✓ Created Next.js project '{project_name}' at {project_dir}\n\nRun 'preview' action to start development server on port {port}."
        
        elif action == "update":
            if not project_dir.exists():
                return f"✗ Project '{project_name}' not found. Use 'create' first."
            
            if not files:
                return f"✗ No files provided for update operation"
            
            updated_files = []
            for filename, content in files.items():
                file_path = project_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding='utf-8')
                updated_files.append(filename)
            
            return f"✓ Updated {len(updated_files)} file(s) in '{project_name}':\n" + "\n".join(f"  • {f}" for f in updated_files)
        
        elif action == "preview":
            if not project_dir.exists():
                return f"✗ Project '{project_name}' not found. Use 'create' first."
            
            # Check if npm is installed
            npm_check = subprocess.run(
                ["npm", "--version"],
                capture_output=True,
                text=True
            )
            
            if npm_check.returncode != 0:
                return f"✗ npm not found. Please install Node.js to use React sandbox."
            
            # Install dependencies if needed
            if not (project_dir / "node_modules").exists():
                logger.info(f"Installing dependencies for {project_name}...")
                install_result = subprocess.run(
                    ["npm", "install"],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if install_result.returncode != 0:
                    return f"✗ Failed to install dependencies:\n{install_result.stderr}"
            
            # Start dev server in background
            preview_url = f"http://localhost:{port}"
            
            # Note: In production, this would start a background process
            # For now, we return the command to run
            return f"""✓ React sandbox ready for '{project_name}'!

**Preview URL:** {preview_url}

**To start the development server, run:**
```bash
cd {project_dir}
npm run dev
```

The preview will be available at {preview_url} and will hot-reload on file changes."""
        
        elif action == "stop":
            # In a full implementation, this would kill the dev server process
            return f"✓ Stopped preview server for '{project_name}' (if running)"
        
        else:
            return f"✗ Unknown action: {action}. Valid actions: create, update, preview, stop"
    
    except subprocess.TimeoutExpired:
        return f"✗ Operation timed out for project '{project_name}'"
    except Exception as e:
        error_msg = f"Error performing {action} for '{project_name}': {repr(e)}"
        logger.error(error_msg)
        return f"✗ {error_msg}"


def get_code_tools():
    """
    Get all code-related tools for the Coder node.
    
    Returns:
        List of enabled code tools
    """
    tools = []
    
    if _is_linux_sandbox_enabled():
        tools.append(linux_sandbox_tool)
        logger.info("Linux sandbox tool enabled")
    
    if _is_file_system_tool_enabled():
        tools.append(file_system_tool)
        logger.info("File system tool enabled")
    
    if _is_react_sandbox_enabled():
        tools.append(react_sandbox_tool)
        logger.info("React sandbox tool enabled")
    
    return tools
