# DeerFlow Integration Attribution

This project integrates components from ByteDance's DeerFlow project, which is licensed under the MIT License.

## Original Project Information

- **Project**: DeerFlow (Deep Exploration and Efficient Research Flow)
- **Repository**: https://github.com/bytedance/deer-flow
- **Copyright**: Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
- **License**: MIT License

## MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Integrated Components

The following components from DeerFlow have been integrated and adapted for OneSeek:

1. **Agent Architecture** - Multi-agent orchestration patterns from `src/agents/`
2. **LLM Integration** - LLM provider factory and configuration from `src/llms/`
3. **Graph Workflow** - LangGraph workflow patterns from `src/graph/`
4. **Tool System** - Tool interception and management from `src/agents/tool_interceptor.py`
5. **Configuration System** - YAML and environment variable configuration from `src/config/`
6. **Prompt Templates** - Dynamic prompt injection middleware from `src/agents/agents.py`

## Modifications

Components have been adapted to:
- Integrate with OneSeek's existing VLLM configuration
- Maintain compatibility with current tool ecosystem (Vespa, Tavily, DuckDuckGo)
- Preserve OneSeek's FastAPI server architecture
- Support OneSeek's streaming and transparency features

## Acknowledgments

We are grateful to ByteDance and the DeerFlow community for creating and open-sourcing
this powerful deep research framework. This integration builds upon their incredible work
while adapting it for OneSeek's local-first, VLLM-based architecture.
