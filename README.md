
# ipy_agent

`ipy_agent` is a Python package that implements an AI agent designed to be integrated into any IPython shell (terminal, Jupyter notebook, QtConsole, etc.).

## Features

- The agent captures all inputs and outputs occurring in the session to populate its context (up to token limit). 
- Use magic commands `%ai` and `%%ai` to interact with the agent using natural language.
- The assistant uses Whisper for multilingual voice synthesis.
- Hold `<ctrl>+<space>` to record and transcribe your voice into text inserted at cursor position. Useful to speak out your prompts instead of typing them. Once active, it can be used wherever the cursor can go, not just in the notebook. (uses pynput for global keyboard hotkey detection. requires proper permissions to do so.)
- The agent can autonomously execute Python code within the session.
- Can be accessed as a declared object in the session, allowing configuration changes or method execution programmatically.
- Can be used as a smart Python function returning any kind of data/object.
- Supports various LLM providers and models via [litellm](https://www.litellm.ai/).
- Integrated tools: The assistant can stream markdown with LaTeX support (in a notebook), talk to you using text to speech, create new code cells in notebooks, observe and extract content (folder, files, URL), introspect python entities (variables, functions, objects, classes, modules...), perform Google searches, perform semantic retrieval using a custom RAG document store (raw text or structured JSON), open files and urls in the browser, open files in a text editor, scrap the web and interact with webpages using a selenium webdriver...
- Has a long term memory (json data) supporting auto retrieval that can be edited dynamically and used to remember data on the long run. 
- Custom tools: you can extend the agent's functionalities by defining your own custom tools.

## Installation

```bash
pip install ipy-agent
```

## Setup

First, you need to set the API keys for your preferred LLM providers as environment variables.
Refer to the [litellm](https://www.litellm.ai/) documentation to know the correct names for your environment variables to be recognized.

In case you want the agent to be able to use the websearch tool you will also need to setup a Google custom search engine and provide these two API keys:

```bash
GOOGLE_CUSTOM_SEARCH_API_KEY="..."
GOOGLE_CUSTOM_SEARCH_CX="..."
```

These API keys can be placed in your .bashrc, directly in your python code via `os.environ` (not recommended), or provided via a .env file and loaded with python-dotenv for instance.

## Usage

Assuming your API keys are properly set up, integration into the IPython session (such as a Jupyter notebook) is as simple as running:

```python
from ipy_agent import IPyAgent
IPyAgent(name="Jarvis", username="Baptiste");
```

Once loaded, the agent can be accessed in the namespace by the name you gave it in lowercase (`jarvis` in this case) and will respond to line and cell magics `%ai` and `%%ai` respectively. If no custom name is provided, the agent will be accessible by default as `agent`.

Alternatively, you may run the command `ipy_agent` directly in the terminal. This will open a new terminal IPython session with the agent already loaded with default configuration. (Just be aware that voice dictation via `<ctrl>+<space>` tend to freeze the terminal IPython shell.)


### Configuration

You can customize the agent by modifying its configuration. Here are some examples:

```python
jarvis.config.model = "claude-3-opus-20240229"  # Use Claude-3 LLM model
jarvis.config.temperature = 0.7  # Adjust the model temperature
jarvis.config.voice_enabled=True # Activate text to speech
jarvis.config.language = 'en'  # Set default language to English
```

### Usage Examples

#### Simple Conversation

```python
%ai Hello Jarvis! I am a novice user. Can you explain what I should know about you?
```

#### Code Execution

```python
%%ai
What is the factorial of 6?
```
The agent will run the adequate python code as a response to computational tasks.

#### Smart Function

You can use the agent as a smart python function:

```python
even_list = jarvis("Return a list of n even numbers", n=5)
even_list # Output: [0, 2, 4, 6, 8]
```

When doing so, the agent's markdown output will be silenced and only the result of computations will be returned.

### Available Tools

The agent provides several built-in tools to ease various tasks. These tools are primarily intended for the agent's usage but can also be used by the user. Here is a list of available tools:

- `agent.observe(source)` : Extracts information from a folder, file, URL, variable, function, class, or module, and injects it into the agent's context.
- `agent.get_text(source)` : Extracts and returns text from a folder, file, URL, variable, function, class, or module.
- `agent.new_code_cell(code)` : Adds a new code cell in the notebook with the specified code.
- `agent.websearch(query, num=5, type='web', start=1)` : Performs a Google search and observe the results.
- `agent.webdriver()` : Creates and returns a selenium webdriver object configured for web automation tasks.
- `agent.edit(file=None,text=None)` : Open a text/code editor to let you edit some content.
- `agent.document_store` : Interface with the custom document store for semantic retrieval and document management (text or JSON).
- `agent.memory`: A special memory storage for the AI assistant. Can be accessed as a nested dict and supports semantic search or auto-retrieval.
- `agent.open(file_or_url)` : Opens any file or url with your default webbrowser.
- `agent.add_tool(name,obj,description)` : Add a new custom tool to the agent, provided a name, a pyhton function or object as `obj`, and a complete description of the tool (signature, methods, example...)

These tools are designed to offer maximum flexibility and facilitate various interactions in the IPython session. Feel free to use them directly in your scripts to leverage their advanced functionalities.

### Contribution

Contributions are welcome! If you wish to contribute to this project, please follow these instructions:

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
