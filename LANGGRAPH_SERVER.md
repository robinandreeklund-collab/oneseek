# LangGraph Server Setup

This document describes how to start and use the LangGraph development server for DeerFlow.

## Prerequisites

Make sure you have installed all dependencies:

```bash
# Install project dependencies
pip install -e .

# Install LangGraph CLI with in-memory support
pip install -U "langgraph-cli[inmem]"
```

## Starting the LangGraph Server

To start the LangGraph development server:

```bash
langgraph dev
```

This will:
- Start the API server at `http://127.0.0.1:2024`
- Open LangGraph Studio UI in your browser at `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`
- Provide API documentation at `http://127.0.0.1:2024/docs`

## Configuration

The LangGraph server is configured through `langgraph.json`:

```json
{
  "dependencies": [
    "."
  ],
  "graphs": {
    "deer_flow": "./backend/deer_flow/workflow.py:graph"
  },
  "env": ".env.deer",
  "python_version": "3.12"
}
```

### Configuration Fields

- **dependencies**: Python packages or local modules required for the graph
- **graphs**: Maps graph names to their implementations (format: `path/to/file.py:variable`)
- **env**: Path to environment variables file
- **python_version**: Required Python version

## Environment Variables

The server loads environment variables from `.env.deer`. Make sure this file exists and contains the necessary configuration for your DeerFlow installation.

## Using the API

Once the server is running, you can:

1. **Access the API**: Use the REST API at `http://127.0.0.1:2024`
2. **View Documentation**: Open `http://127.0.0.1:2024/docs` for interactive API docs
3. **Use Studio UI**: Access the visual interface at the URL provided in the console

## Troubleshooting

### Server won't start

If you see errors like:
```
TypeError: JsonPlusSerializer.__init__() got an unexpected keyword argument 'allowed_json_modules'
```

This indicates version incompatibility. Make sure you have the correct versions installed:
- `langgraph-checkpoint>=4.0.0`
- `langgraph-checkpoint-mongodb>=0.3.0`
- `langgraph-checkpoint-postgres>=3.0.0`

To fix, run:
```bash
pip install -U langgraph-checkpoint-mongodb>=0.3.0 langgraph-checkpoint-postgres>=3.0.0
```

### Dependencies conflict

If you see dependency conflicts during installation, try:
```bash
pip install -e . --force-reinstall
```

## Development

The in-memory server is designed for development and testing. For production use, consider:
- Using LangSmith Deployment
- Setting up proper checkpoint persistence with PostgreSQL or MongoDB
- Configuring proper authentication and security

## More Information

- [LangGraph Documentation](https://docs.langchain.com/oss/python/langgraph/)
- [LangGraph CLI Documentation](https://docs.langchain.com/langsmith/cli)
- [DeerFlow Documentation](./SNABBSTART_DEERFLOW.md)
