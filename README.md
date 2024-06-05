
# ipy_agent

`ipy_agent` is a Python package that implements an AI agent designed to be integrated into any IPython shell (terminal, Jupyter notebook, QtConsole, etc.).

## Features

- The agent captures all inputs and outputs occurring in the session to populate its context (up to token limit). 
- Use magic commands `%ai` and `%%ai` to interact with the agent using natural language.
- The assistant uses OpenAI's Whisper API for multilingual voice synthesis (OpenAI API key required to use it).
- Hold `<ctrl>+<space>` to record and transcribe your voice into text inserted at cursor position. Useful to speak out your prompts instead of typing them. Once active, it can be used wherever the cursor can go, not just in the notebook. (uses pynput for global keyboard hotkey detection. requires proper permissions to do so.)
- The agent can autonomously execute Python code within the session.
- Can be accessed as an object in the session, allowing configuration changes or method execution programmatically.
- Can be used as a smart Python function returning any kind of data/object.
- Supports various LLM providers and models via [litellm](https://www.litellm.ai/).
- Integrated tools: The assistant can stream markdown with LaTeX support (in a notebook), talk to you using text to speech, create new code cells in notebooks, observe and extract content (folder, files, URL), introspect python entities (variables, functions, objects, classes, modules...), perform Google searches, perform semantic retrieval using a custom RAG document store (raw text or structured JSON), open files and urls in the browser, open files in a text editor, scrap the web and interact with webpages using a selenium webdriver...
- Has a long term memory (json data) supporting auto retrieval that can be edited dynamically and used to remember data on the long run. 
- Custom tools: you can extend the agent's functionalities by defining your own custom tools.

## Installation

```bash
pip install ipy-agent
```

## Usage

Integration into the IPython session (such as a Jupyter notebook) is as simple as running:

```python
from ipy_agent import IPyAgent
IPyAgent();
```

Once loaded, the agent can be accessed in the namespace as `agent` and will respond to line and cell magics `%ai` and `%%ai` respectively.

Alternatively, you may run the command `ipy_agent` directly in the terminal. This will open a new terminal IPython session with the agent already loaded with default configuration. (Just be aware that voice dictation via `<ctrl>+<space>` tend to freeze the terminal IPython shell.)

## Constructor

Here are the accepted parameters of the agent's constructor.

```python
IPyAgent(name=None,username=None,preprompt=None,workfolder=None,shell=None,**kwargs)
```

- `name` (string) gives a custom name to your agent, default is 'Agent'. This won't affect the agent object's name in the session.
- `username` (string) tells the agent how it should call you. Default is 'User'.
- `preprompt` (string) passes a custom preprompt (initial system message with instructions) to the agent. This will replace the default preprompt you can find as default_preprompt.txt in the package folder.
- `workfolder` (path string) the folder the agent will be using to store files it creates. Defaults to `~/IPyAgent'. The folder will be created if it doesn't exist. This is also where you will find the agent's startup script and .env file.
- `shell` (IPython shell object) The shell object in which the agent will be loaded in. Defaults to the the shell returned by IPython.get_ipython().
- `**kwargs` additional kwargs will update the agent.config dict.

## Setup

First, you need to set the API keys for your preferred LLM providers as environment variables.

At startup, the agent will attempt to read the .env file found in its workfolder (`~/IPyAgent` by default) to load the various API keys it will use.
This file will initially be created empty and should be configured before the agent can run smoothly. In case it is left empty, an exception will be raised, asking you to configure it.

Refer to the [litellm](https://www.litellm.ai/) documentation to know the correct names for your environment variables to be recognized.

In case you want the agent to be able to use the websearch tool you will also need to setup a Google custom search engine and provide adequate API keys.

Example:
```
# .env

OPENAI_API_KEY="..." (required for TTS and default GPT-4o model)
ANTHROPIC_API_KEY="..." (in case you want to use Claude3 models)
GOOGLE_CUSTOM_SEARCH_API_KEY="..." (required for the websearch tool)
GOOGLE_CUSTOM_SEARCH_CX="..." (required for the websearch tool)

# Add here any other API keys you will use (in custom tools for instance)

```

You will also find a startup.py file. This file will be executed whenever the agent is loaded. You can use it to preload custom tools you want to permanently add to the agent.

Example:

```python
# startup.py

def sum_tool(a,b):
    return a+b

agent.add_tool(
    name="sum",
    obj=sum_tool,
    description="agent.sum(a,b) # This tool returns the sum of two numbers a and b."
)
```

### Configuration

Once loaded in the session, you can customize the agent by modifying its agent.config dict (supports attribute syntax). Here are some examples:

```python
agent.config.model = "claude-3-opus-20240229"  # Use Claude-3 LLM model
agent.config.temperature = 0.7  # Adjust the model temperature
agent.config.voice_enabled=True # Activate text to speech
agent.config.voice='shimmer' # The voice used for TTS. 
agent.config.language = 'en'  # Set default language to English
```

### Usage Examples

#### Simple Conversation

```python
%ai Hello Agent! I am a new user. Can you explain what I should know about you?
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
even_list = agent("Return a list of n even numbers", n=5)
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

### Contribution

Contributions are welcome! If you wish to contribute to this project, please follow these instructions:

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
