import os
from IPython import get_ipython
import tiktoken
from .attrdict import AttrDict
from datetime import datetime
import re

os.environ['ROOT_PATH']=os.path.dirname(os.path.abspath(__file__))

def root_join(*args):
    return os.path.join(os.getenv('ROOT_PATH'),*args)

def text_content(file):
    if os.path.isfile(file):
        with open(file) as f:
            return f.read()
    else:
        return None

def is_notebook_shell(shell=None):
    try:
        shell=shell or get_ipython()
        sh_type=shell_type(shell)
        if sh_type == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif sh_type == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (e.g., IDLE)
    except NameError:
        return False      # Not running in IPython
    
def shell_type(shell):
    if shell:
        return shell.__class__.__name__
    else:
        return None

tokenizer = tiktoken.get_encoding("cl100k_base")

def tokenize(string):
    int_tokens = tokenizer.encode(string)
    str_tokens = [tokenizer.decode([int_token]) for int_token in int_tokens]
    return str_tokens

def token_count(string):
    return len(tokenizer.encode(string))

def Message(content, role, name, type, lasting=0):
    return AttrDict(content=content, role=role, name=name, type=type, lasting=lasting, timestamp=datetime.now().isoformat())

def sort(messages):
    return sorted(messages, key=lambda msg: msg.timestamp)

def truncate(string, max_tokens=2000):
    tokens = tokenize(string)
    if len(tokens) > max_tokens:
        removed = len(tokens) - max_tokens
        truncated = tokens[:max_tokens // 2] + [f"\n\n#####\n\n[Maximal message size reached: {removed} tokens truncated]\n\n#####\n\n"] + tokens[-max_tokens // 2:]
        return ''.join(truncated)
    else:
        return string

def pack_msgs(messages):
    text = ''
    for message in messages:
        text += message.name + ':\n'
        text += message.content.strip() + '\n\n'
    return text

def total_tokens(messages):
    return token_count(pack_msgs(messages))

def extract_python(text, pattern=None):
    pattern = pattern or r'```run_python(.*?)```'
    iterator = re.finditer(pattern, text, re.DOTALL)
    return [match.group(1) for match in iterator]

def format(string, context=None):
    # Si aucun contexte n'est fourni, utiliser un dictionnaire vide
    if context is None:
        context = {}
    # Trouver les expressions entre <<<...>>>
    def replace_expr(match):
        expr = match.group(1)
        try:
            # Évaluer l'expression dans le contexte donné et la convertir en chaîne
            return str(eval(expr, context))
        except Exception as e:
            # print(f"could not evaluate expr: {expr}\n Exception:\n {str(e)}")
            # En cas d'erreur, retourner l'expression non évaluée
            return '<<<' + expr + '>>>'
    # Remplacer chaque expression par son évaluation
    return re.sub(r'<<<(.*?)>>>', replace_expr, string)
