from .utils import Message
import sys

class MsgCollector:

    def __init__(self, agent):
        self.agent = agent
        self.current_message = None
        self.id=0

    def collect(self, msg):
        if msg.role=='user':
            msg.content+='\n'
        if self.current_message is None or msg.name != self.current_message.name:
            self.dump_message()
            self.current_message = msg
            if msg.role=='assistant' and not self.agent.silent:
                self.agent.display_md(msg.content)
        else:
            self.current_message.content += msg.content
            if msg.role=='assistant' and not self.agent.silent:
                self.agent.display_md(msg.content,update=True)

    def dump_message(self):
        if self.current_message:
            self.agent.add_message(self.current_message)
            self.current_message = None

class CollectIO:

    redirections=[]

    def __init__(self, agent, role, name):
        self.agent = agent
        self.saved_role=self.agent.current_role
        self.saved_name=self.agent.current_name
        self.role = role
        self.name = name
        self.saved_stdout = sys.stdout
        self.saved_stderr = sys.stderr

    def collect(self,data):
        self.agent.collector.collect(Message(content=data, role=self.role, name=self.name, type="queued"))

    def write(self, data):
        if data:
            if self is CollectIO.redirections[-1] and self.agent.capture:
                self.collect(data)
            self.saved_stdout.write(data)

    def flush(self):
        self.saved_stdout.flush()

    def flush_err(self):
        self.saved_stderr.flush()

    def __enter__(self):
        CollectIO.redirections.append(self)
        self.agent.current_role=self.role
        self.agent.current_name=self.name
        sys.stdout = self
        sys.stderr = self
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self.saved_stdout
        sys.stderr = self.saved_stderr
        self.agent.current_role=self.saved_role
        self.agent.current_name=self.saved_name
        CollectIO.redirections.pop(-1)