from IPython.display import display, Markdown
from IPython.core.magic import register_line_cell_magic
from IPython import get_ipython
import os
                        
def is_notebook():
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (e.g., IDLE)
    except NameError:
        return False      # Not running in IPython
    
class MarkdownOutput:

    def __init__(self):
        self.current_id=0
        self.current_content=''
        self.is_notebook=is_notebook()

    def display(self,string,update=False):
        if self.is_notebook:
            if update:
                self.current_content+=string
                display(Markdown(self.current_content.replace("```run_python","```python").replace('\\)','$').replace('\\(','$').replace('\\[','$$').replace('\\]','$$')),display_id=str(self.current_id),update=True)
            else:
                self.current_id+=1
                self.current_content=string
                display(Markdown(self.current_content.replace("```run_python","```python").replace('\\)','$').replace('\\(','$').replace('\\[','$$').replace('\\]','$$')),display_id=str(self.current_id))
        else:
            print(string,end='',flush=True)

_md_output=MarkdownOutput()

def display_md(string,update=False):
    _md_output.display(string,update)

def new_code_cell(code):
    get_ipython().set_next_input(code)

@register_line_cell_magic
def ai(line, cell=''):
    if line:
        prompt=line+'\n'+cell
    else:
        prompt=cell
    get_ipython().user_ns['<<<self.instance_name>>>'](None,silent=False)
