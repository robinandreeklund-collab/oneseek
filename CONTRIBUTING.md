# Contributing to OneSeek.ai

Thank you for your interest in contributing to OneSeek.ai! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- NVIDIA GPU with ≥24GB VRAM (for local LLM inference)
- Git

### Quick Setup

Use the provided setup script:

```bash
./setup.sh
```

Or follow manual setup in README.md.

## Project Structure

```
oneseek/
├── backend/          # Python FastAPI + LangGraph
├── frontend/         # Next.js + React + TypeScript
├── setup.sh          # Quick setup script
└── docker-compose.yml # Docker orchestration
```

## Development Workflow

### Backend Development

1. Activate virtual environment:
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. Run tests:
```bash
python test_setup.py
```

3. Start development server:
```bash
uvicorn app:app --reload --port 8001
```

4. Test endpoints:
```bash
curl http://localhost:8001/health
```

### Frontend Development

1. Install dependencies:
```bash
cd frontend
npm install  # or yarn install
```

2. Start development server:
```bash
npm run dev  # or yarn dev
```

3. Build for production:
```bash
npm run build
```

4. Run linter:
```bash
npm run lint
```

## Code Style

### Python

- Follow PEP 8 style guide
- Use type hints where appropriate
- Docstrings for all public functions and classes
- Maximum line length: 100 characters

Example:
```python
def process_message(content: str, max_length: int = 2048) -> str:
    """
    Process a message and return formatted output.
    
    Args:
        content: The message content to process
        max_length: Maximum length of the output
        
    Returns:
        Formatted message string
    """
    return content[:max_length]
```

### TypeScript/React

- Use TypeScript for all new code
- Follow React best practices
- Use functional components with hooks
- Descriptive variable and function names

Example:
```typescript
interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export function ChatMessage({ role, content }: ChatMessage) {
  return (
    <div className={cn("message", role)}>
      {content}
    </div>
  );
}
```

## Adding Features

### Backend Features

1. Add new endpoints in `backend/app.py`
2. Implement business logic in appropriate modules
3. Update agent workflow in `backend/agent.py` if needed
4. Add tests for new functionality
5. Update API documentation

### Frontend Features

1. Create new components in `src/components/`
2. Use existing UI components from shadcn/ui when possible
3. Maintain dark/light theme support
4. Test on both themes
5. Update component documentation

## Testing

### Backend Testing

Currently, tests are minimal. To add tests:

1. Create `backend/tests/` directory
2. Use pytest framework
3. Test coverage for:
   - API endpoints
   - Agent workflow
   - Vespa integration

Example:
```python
import pytest
from app import app
from fastapi.testclient import client

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

### Frontend Testing

To add tests:

1. Use Jest + React Testing Library
2. Test components in isolation
3. Test user interactions

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Test your changes thoroughly
5. Commit with clear messages: `git commit -m "Add feature: description"`
6. Push to your fork: `git push origin feature/your-feature-name`
7. Open a Pull Request with description of changes

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Comments added for complex logic
- [ ] Documentation updated if needed
- [ ] No console errors or warnings
- [ ] Tested locally
- [ ] PR description clearly explains changes

## Reporting Issues

### Bug Reports

Include:
- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python/Node version, GPU)
- Error messages and logs
- Screenshots if applicable

### Feature Requests

Include:
- Clear description of the feature
- Use case / motivation
- Proposed implementation (optional)
- Impact on existing features

## Areas for Contribution

### High Priority

- [ ] Streaming responses from vLLM to frontend
- [ ] Better error handling and retry logic
- [ ] Comprehensive test coverage
- [ ] Performance optimization for large chat histories
- [ ] Better Vespa error handling

### Medium Priority

- [ ] Multi-LLM comparison mode
- [ ] Export chat history
- [ ] More embedding models support
- [ ] Better mobile responsiveness
- [ ] Keyboard shortcuts

### Nice to Have

- [ ] Voice input/output
- [ ] Code syntax highlighting in messages
- [ ] Image generation integration
- [ ] Plugin system for custom tools
- [ ] Multi-language UI support

## Community

- GitHub Issues: Bug reports and feature requests
- Discussions: General questions and ideas

## License

By contributing to OneSeek.ai, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue for questions about contributing!
