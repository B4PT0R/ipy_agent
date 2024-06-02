from IPython import get_ipython
from IPython.terminal.interactiveshell import TerminalInteractiveShell
from .llm_client import LLMClient
from .attrdict import AttrDict
import traceback
from functools import wraps
from .retrieval import DocumentStore
from .dictation import Dictation
from .msg_collector import MsgCollector,CollectIO
from .tools import get_text, init_tools
from .utils import root_join,Message,text_content,shell_type,truncate,pack_msgs,total_tokens,sort,extract_python,format
from .voice import VoiceProcessor
from textwrap import dedent
import os

class IPyAgent:
    default_config = AttrDict(
        model="gpt-4o",
        max_tokens=4000,
        token_limit=32000,
        temperature=1,
        top_p=1,
        language='fr',
        voice_enabled=True,
        voice="shimmer"
    )

    def __init__(self, name=None, username=None, preprompt=None, workfolder=None, shell=None, **kwargs):
        self.client = LLMClient()
        self.config = IPyAgent.default_config
        self.config.update(**kwargs)
        self.messages = []
        self.collector = MsgCollector(self)
        self.voice=VoiceProcessor(self)
        self.name = name or "Agent"
        self.instance_name=self.name.lower()
        self.capture=True
        self.username=username or "User"
        self.current_role = "user"  # Initialisation du rôle courant
        self.current_name=self.username
        self.tools=AttrDict()
        self.init_workfolder(workfolder=workfolder)
        self.store=DocumentStore(folder=os.path.join(self.workfolder,"documents"))
        self.add_message(Message(content=preprompt or text_content(root_join("default_preprompt.txt")), role="system", name="Instructions", type="header"))
        self.init_files()
        self.init_shell(shell=shell)
        self.init_tools()
        self.run_startup()
        self.dictation=Dictation(self)
        self.dictation.start()

    def __getattr__(self,attr):
        if attr in self.tools:
            return self.tools[attr]
        else:
            super().__getattribute__(attr)

    def init_workfolder(self,workfolder=None):
        workfolder=workfolder or os.path.expanduser("~/IPyAgent")
        if not os.path.isdir(workfolder):
            os.makedirs(workfolder)
        self.workfolder=workfolder
        path=os.path.join(self.workfolder,"documents")
        if not os.path.isdir(path):
            os.makedirs(path)

    def init_files(self):
        if not "memory" in self.store.get_titles():
            self.store.new_document(type="json",title="memory",content=dict(),description="Memory storage of the AI assistant")
        self.store.load_document("memory")
        path=os.path.join(self.workfolder,"startup.py")
        if not os.path.isfile(path):
            open(path,'w').close()

    def run_startup(self):
        path=os.path.join(self.workfolder,"startup.py")
        with open(path) as f:
            code=f.read()
        if code:
            self.run_cell(code)

    def init_shell(self,shell=None):

        self.shell = shell or get_ipython() or TerminalInteractiveShell.instance()

        # Injecter l'agent dans l'espace de noms de la console
        self.shell.user_ns[self.instance_name] = self

        # Define the magic commands to call the assistant from the console/notebook
        self.shell.run_cell(format(text_content(root_join("init_shell.py")),context=locals()))

        # Save the original run_cell method
        self.run_cell = self.shell.run_cell
        
        # Decorate it with input/output capture towards the assistant's message history
        @wraps(self.run_cell)
        def run_cell_with_capture(*args, **kwargs):
            code = args[0]
            if code.strip():
                if self.current_role == "user":
                    self.collector.collect(Message(content=code, role=self.current_role, name=self.current_name, type="queued"))
                try:
                    with CollectIO(self, role="system", name="Interpreter"):
                        result = self.run_cell(code, *args[1:], **kwargs)
                        if result.error_in_exec is not None:
                            # Capture the traceback and inject it to the agent's context
                            traceback_details = traceback.format_exception(type(result.error_in_exec), result.error_in_exec, result.error_in_exec.__traceback__)
                            tb_str = "".join(traceback_details)
                            self.collector.collect(Message(content=tb_str, role="system", name="Interpreter", type="queued"))
                        elif result.result:
                            # Capture the execution result and inject it to the agent's context
                            self.collector.collect(Message(content=str(result.result), role="system", name="Interpreter", type="queued"))
                except Exception as e:
                    if self.current_role=='assistant':
                        # Ensures the agent's process continues after an exception
                        tb_str = traceback.format_exc()
                        self.collector.collect(Message(content=tb_str, role="system", name="Interpreter", type="queued"))
                        result = None  
                    else:
                        raise e
            return result

        # Override the shell.run_cell method with the decorated one
        self.shell.run_cell = run_cell_with_capture

        # Finished initializing
        self.display_md(dedent(
            f"""
            The IPyAgent is ready, declared as `{self.instance_name}` in the console. 

            Use `%ai` or `%%ai` magics to interact, or call its methods programatically.

            Hold `<ctrl>+<space>` to dictate text from voice and insert it wherever the cursor is.

            Ask for help at any time by running `%ai help` or `%ai <your question>`.
            """
        ))

    @property
    def shell_type(self):
        return shell_type(self.shell)

    def init_tools(self):
        init_tools(self)
        
    def observe(self,data,lasting=3):
        text=get_text(data)
        self.collector.collect(Message(content=text,role="system",name="Observation",type='temp',lasting=lasting))
        self.new_turn=True

    def add_message(self, msg):
        msg.content = truncate(msg.content.strip(), max_tokens=self.config.max_tokens)
        if msg.role == "assistant":
            msg.content += "\n#SUBMIT#"
        self.messages.append(msg)

    def add_tool(self, name, obj, description,no_add=False):
        self.tools.update({name:obj})
        self.add_message(Message(content=description, role="system", name="Tool", type="header"))

    def get_messages(self, type="all"):
        if type == "all":
            return self.messages
        else:
            return [msg for msg in self.messages if msg.type == type]
        
    def get_retrieved(self):
        query=pack_msgs(self.get_messages(type="queued")[-2:])
        results=self.store.search(query,num=15,threshold=0.4)
        if results:
            return [Message(content=f"Document Store's current auto-retrieval results:\n {repr(results)}",role="system",name="Retrieval",type='temp',lasting=1)]
        else:
            return []

    def reduce_lasting(self):
        msgs=[]
        for msg in self.messages:
            if msg.lasting==0:
                msgs.append(msg)
            elif msg.lasting==1:
                pass
            else:
                msg.lasting-=1
                msgs.append(msg)
        self.messages = msgs

    def gen_context(self):
        headers=[Message(content=format(header.content,context={'self':self,'agent':self,**globals()}),role=header.role,name=header.name,type=header.type) for header in self.get_messages(type="header")]
        queued = self.get_messages(type="queued")
        temp=self.get_messages(type="temp")
        retrieved=self.get_retrieved()

        current_count = total_tokens(headers + temp + retrieved)
        context_limit = self.config.token_limit - self.config.max_tokens
        available_tokens = context_limit - current_count

        recent = []
        tokens = 0

        for msg in reversed(queued):
            msg_tokens = total_tokens([msg])
            if tokens + msg_tokens <= available_tokens:
                tokens += msg_tokens
                recent.append(msg)
            else:
                break
        context = headers + sort(temp + recent + retrieved)
        self.reduce_lasting()
        return context

    def stream_response(self):
        self.collector.dump_message()

        params = dict(
            messages=self.gen_context(),
            model=self.config.model,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            max_tokens=self.config.max_tokens,
            stop=["#SUBMIT#"]
        )

        self.capture=False
        for token in self.voice.speak(self.client.streamed_completion(**params)):
            self.collector.collect(Message(content=token,role="assistant",name=self.name,type="queued"))
        self.collector.collect(Message(content='\n',role="assistant",name=self.name,type="queued"))
        self.capture=True
        self.collector.dump_message()

    def set_data_output(self,data):
        self.data_output=data

    def run_agent_code(self, code):
        self.shell.run_cell(code)

    def display_md(self,string,update=False):
        self.shell.user_ns['display_md'](string,update)

    def new_code_cell(self,code):
        self.shell.user_ns['new_code_cell'](code)

    def process(self):
        self.new_turn = False

        self.stream_response()

        python_parts = extract_python(self.messages[-1].content)
        if python_parts:
            self.new_turn = True
            for code in python_parts:
                self.run_agent_code(code)
        
        if self.new_turn:
            self.process()

    def __call__(self,prompt=None,silent=True,**kwargs):
        self.data_output=None
        self.silent=silent
        self.call_kwargs=AttrDict(**kwargs)
        self.current_role = "assistant"
        self.current_name=self.name
        if prompt:
            self.collector.collect(Message(content=prompt,role="user",name=self.username,type="queued"))
        self.process()
        self.current_role = "user"
        self.current_name=self.username
        self.silent=False
        return self.data_output

    def interact(self):
        self.shell.mainloop()

