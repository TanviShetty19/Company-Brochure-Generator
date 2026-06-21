# Company Brochure Generator

Automatically generate professional company brochures using LLMs. 
**Default uses Ollama with Llama models - completely free and runs locally!**

## Features

- **Multi-Provider Support**: Ollama (default), OpenAI, or Gemini
- **Free Option**: Use Ollama with local Llama models
- **Smart Link Analysis**: LLM identifies relevant company pages
- **Professional Output**: Generates markdown brochures
- **Caching**: Reduces repeated API calls
- **CLI Interface**: Easy to use from the command line

## Quick Start

### 1. Install Ollama (Default)

```bash
# Visit https://ollama.com and install for your OS

# Pull Llama 3.2 model (recommended for most computers)
ollama pull llama3.2:1b

# Alternative models
# ollama pull deepseek-r1:1.5b
# ollama pull phi3:mini