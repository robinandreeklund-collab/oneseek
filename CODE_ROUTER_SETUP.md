# Code Router and Live Development Tools - Setup Guide

This guide describes the new code router and extended development tools for OneSeek's LangGraph implementation.

## Overview

The code router enables intelligent handling of code-related questions in LangGraph. When users ask programming or development questions, the system now routes them through a specialized workflow that provides:

- **Smart Routing**: Automatic detection of code-related questions
- **Linux Sandbox Environment**: Isolated execution environments using WSL/Docker
- **File System Management**: Read/write access to project files
- **Live React Sandbox**: Real-time Next.js application preview
- **Human-in-the-Loop**: Optional clarification for unclear code tasks

## Architecture

### Routing Flow

```
User Question
    ↓
Coordinator (detects code questions)
    ↓
handoff_to_coder tool called
    ↓
├─ [clarity="clear"] → Planner (creates code execution plan)
│                          ↓
│                      Research Team
│                          ↓
│                      Coder Node (executes with extended tools)
│                          ↓
│                      Reporter
│
└─ [clarity="unclear"] → Human Feedback
                             ↓
                         Planner (after clarification)
                             ↓
                         ... (continues as above)
```

### Code Detection

The coordinator uses the `handoff_to_coder` tool when it detects:
- Programming language keywords (Python, JavaScript, Java, etc.)
- Development terms (code, programming, debug, compile, etc.)
- Framework names (React, Django, Next.js, etc.)
- Development actions (write code, create app, build, deploy, etc.)

## Installation & Setup

### Prerequisites

#### Required
- **Python 3.11+**
- **Node.js 18+** (for React sandbox)
- **OneSeek backend** already installed and running

#### Optional (for full functionality)
- **Windows with WSL 2** (for Linux sandbox on Windows)
- **Docker** (alternative to WSL or for additional containerization)
- **npm/yarn** (for React/Next.js development)

### Step 1: Install Python Dependencies

The code tools are already included in the DeerFlow package. No additional Python packages are required beyond the existing `requirements.txt`.

### Step 2: Enable Code Tools

Create or update your `.env` file in the `backend/` directory:

```bash
# Enable Python REPL (already available)
ENABLE_PYTHON_REPL=true

# Enable Linux Sandbox Environment
ENABLE_LINUX_SANDBOX=true

# Enable File System Management Tool
ENABLE_FILE_SYSTEM_TOOL=true

# Enable React Sandbox for Next.js preview
ENABLE_REACT_SANDBOX=true

# Optional: Workspace directories
CODE_WORKSPACE_ROOT=/path/to/your/workspace
REACT_SANDBOX_ROOT=/path/to/react/sandboxes
```

### Step 3: Setup WSL (Windows Users)

If you're on Windows and want to use the Linux sandbox:

1. **Install WSL 2**:
   ```powershell
   wsl --install
   ```

2. **Verify WSL is working**:
   ```powershell
   wsl --status
   ```

3. **Install Ubuntu** (or your preferred distro):
   ```powershell
   wsl --install -d Ubuntu
   ```

### Step 4: Setup Docker (Alternative or Additional)

For containerized execution:

1. **Install Docker Desktop**: https://www.docker.com/products/docker-desktop

2. **Verify Docker is running**:
   ```bash
   docker --version
   docker run hello-world
   ```

3. **Optional**: Set custom Docker image:
   ```bash
   # In your .env file
   DOCKER_SANDBOX_IMAGE=ubuntu:latest
   ```

### Step 5: Restart Backend

Restart the OneSeek backend to load the new configuration:

```bash
cd backend
uvicorn app:app --reload --port 8001
```

## Tool Descriptions

### 1. Linux Sandbox Tool

Executes shell commands in an isolated environment.

**Capabilities**:
- Run bash commands safely
- Compile and test code
- Install packages (apt, pip, npm, etc.)
- Execute scripts

**Example Usage**:
```python
# The agent can use this tool internally
linux_sandbox_tool(
    command="gcc -o myapp myapp.c && ./myapp",
    working_dir="/tmp/build"
)
```

**Behind the scenes**:
- Tries WSL first (if available on Windows)
- Falls back to Docker if WSL not available
- 30-second timeout for safety
- Returns stdout/stderr

### 2. File System Tool

Manages files and directories in a safe workspace.

**Operations**:
- `read`: Read file contents
- `write`: Create or update files
- `list`: List directory contents
- `delete`: Remove files or directories
- `create_dir`: Create new directories

**Example Usage**:
```python
# Write a Python file
file_system_tool(
    operation="write",
    path="src/main.py",
    content="print('Hello, World!')"
)

# Read it back
file_system_tool(
    operation="read",
    path="src/main.py"
)
```

**Security**:
- All operations are scoped to `CODE_WORKSPACE_ROOT`
- Path traversal attacks are prevented
- Default workspace: `/tmp/oneseek_workspace`

### 3. React Sandbox Tool

Creates and manages live Next.js/React projects.

**Actions**:
- `create`: Initialize a new Next.js project
- `update`: Modify project files
- `preview`: Start development server
- `stop`: Stop the preview server

**Example Usage**:
```python
# Create a new Next.js project
react_sandbox_tool(
    action="create",
    project_name="my-app",
    files={
        "src/app/page.tsx": "export default function Home() { return <h1>Hello</h1> }"
    },
    port=3001
)

# Update files
react_sandbox_tool(
    action="update",
    project_name="my-app",
    files={
        "src/app/page.tsx": "export default function Home() { return <h1>Updated!</h1> }"
    }
)

# Start preview
react_sandbox_tool(
    action="preview",
    project_name="my-app",
    port=3001
)
```

**Features**:
- Automatic project scaffolding
- Hot-reload on file changes
- Custom port assignment
- Isolated project directories

## Frontend Integration

### Live Code Preview Component

A React component for displaying live code previews is planned for future integration.

**Planned features**:
- Embedded iframe for live preview
- Code editor with syntax highlighting
- Real-time synchronization
- Error display and debugging

**Implementation location**: `frontend/src/components/CodePreview.tsx` (to be created)

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_PYTHON_REPL` | `false` | Enable Python code execution |
| `ENABLE_LINUX_SANDBOX` | `false` | Enable Linux sandbox environment |
| `ENABLE_FILE_SYSTEM_TOOL` | `false` | Enable file system management |
| `ENABLE_REACT_SANDBOX` | `false` | Enable React/Next.js sandbox |
| `CODE_WORKSPACE_ROOT` | `/tmp/oneseek_workspace` | Root directory for file operations |
| `REACT_SANDBOX_ROOT` | `/tmp/oneseek_react_sandboxes` | Root directory for React projects |
| `DOCKER_SANDBOX_IMAGE` | `ubuntu:latest` | Docker image for sandbox |

## Testing

### Test Code Routing

Send a code-related question to test the routing:

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Write a Python function to calculate fibonacci numbers"}
    ],
    "stream": false
  }'
```

### Test Linux Sandbox

With `ENABLE_LINUX_SANDBOX=true`, ask:
> "Run the command 'uname -a' to show system information"

### Test File System

With `ENABLE_FILE_SYSTEM_TOOL=true`, ask:
> "Create a file called hello.txt with the content 'Hello, World!'"

### Test React Sandbox

With `ENABLE_REACT_SANDBOX=true`, ask:
> "Create a simple Next.js app with a counter component"

## Troubleshooting

### Issue: "WSL or Docker not found"

**Solution**: 
- On Windows: Install WSL 2
- On Linux/Mac: Install Docker
- Or disable the Linux sandbox: `ENABLE_LINUX_SANDBOX=false`

### Issue: "Tool disabled" messages

**Solution**: Check your `.env` file and ensure the relevant `ENABLE_*` variables are set to `true`.

### Issue: "Path outside workspace" error

**Solution**: The file system tool restricts operations to the workspace directory for security. Set `CODE_WORKSPACE_ROOT` to a suitable location.

### Issue: React sandbox "npm not found"

**Solution**: Install Node.js and npm:
```bash
# Windows (with Chocolatey)
choco install nodejs

# Linux
sudo apt install nodejs npm

# Mac
brew install node
```

### Issue: Code questions not being routed to coder

**Solution**: 
- Ensure your question includes code-related keywords
- The LLM must recognize it as a coding task
- Try being more explicit: "Write code to..." or "Create a program that..."

## Advanced Usage

### Custom Sandbox Images

Create a custom Docker image with your preferred tools:

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    nodejs \
    npm \
    gcc \
    g++ \
    make

WORKDIR /workspace
```

Build and configure:
```bash
docker build -t oneseek-sandbox:latest .
```

Update `.env`:
```bash
DOCKER_SANDBOX_IMAGE=oneseek-sandbox:latest
```

### Extending Tools

To add new code tools:

1. Create a new tool in `backend/deer_flow/tools/code_tools.py`:
   ```python
   @tool
   @log_io
   def my_custom_tool(param: Annotated[str, "Description"]) -> str:
       """Tool description for the LLM."""
       # Implementation
       return result
   ```

2. Add it to `get_code_tools()`:
   ```python
   def get_code_tools():
       tools = []
       # ... existing tools ...
       if _is_my_custom_tool_enabled():
           tools.append(my_custom_tool)
       return tools
   ```

3. Add environment variable check:
   ```python
   def _is_my_custom_tool_enabled() -> bool:
       env_enabled = os.getenv("ENABLE_MY_CUSTOM_TOOL", "false").lower()
       return env_enabled in ("true", "1", "yes", "on")
   ```

## Security Considerations

### Sandboxing

- **Linux Sandbox**: Commands run in isolated WSL/Docker environments
- **File System**: All operations restricted to workspace directory
- **Timeouts**: 30-second execution limit prevents infinite loops
- **Path Validation**: Prevents directory traversal attacks

### Best Practices

1. **Don't enable tools in production** unless you fully understand the security implications
2. **Use dedicated workspace directories** separate from critical system files
3. **Monitor resource usage** - sandbox environments can consume significant resources
4. **Regularly clean workspaces** to prevent disk space issues
5. **Review generated code** before executing in production environments

## Future Enhancements

### Planned Features

- [ ] Frontend live preview component integration
- [ ] Multi-language REPL support (Node.js, Ruby, Go, etc.)
- [ ] Code linting and formatting tools
- [ ] Git integration for version control
- [ ] Container resource limits (CPU, memory)
- [ ] Persistent sandbox sessions
- [ ] Code review and security scanning tools
- [ ] WebAssembly execution environment
- [ ] Collaborative editing support

### Contributing

To contribute to the code router and tools:

1. Fork the repository
2. Create a feature branch
3. Add tests for new tools
4. Update documentation
5. Submit a pull request

## License

MIT License - See [LICENSE](../LICENSE) file

## Support

For questions or issues:
- GitHub Issues: [oneseek/issues](https://github.com/robinandreeklund-collab/oneseek/issues)
- Documentation: See [README.md](../README.md)

---

**Note**: This feature is currently in development. Some functionality may be incomplete or subject to change. Always test in a development environment before deploying to production.
