from textwrap import dedent
from .get_text import get_text
from .get_webdriver import get_webdriver
from .google_search import init_google_search
from IPython import get_ipython
import webbrowser

g_search=init_google_search()

def shell_type(shell):
    if shell:
        return shell.__class__.__name__
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

def init_tools(agent):
    if is_notebook_shell(agent.shell):
        agent.add_tool(
            name="new_code_cell",
            obj=agent.new_code_cell,
            description=dedent("""
            <<<self.instance_name>>>.new_code_cell(code)
            Adds a new cell to the current notebook populated with some code. 
            Useful to let the user review/edit the code before deciding to execute.
            
            Example:
            User:
            %ai Could you show me the code of the factorial function in a new cell, please?

            Assistant:
            Sure thing! Let me create a new code cell to show you how it's done.
            ```run_python
            <<<self.instance_name>>>.new_code_cell(\"\"\"
            def factorial(n):
                if not isinstance(n,int) or n<0:
                    raise ValueError("n must be a positive integer.")
                elif n==0:
                    return 1
                else:
                    return n*factorial(n-1)
            \"\"\")
            ```
            #SUBMIT#
            """)
        )

        def edit(file=None,text=None):
            from IPython.display import display, Javascript
            import os

            file_path=file or os.path.join(os.path.expanduser("~"),"new_buffer.txt")

            if not os.path.isfile(file_path):
                with open(file_path,'w') as f:
                    f.write('')
            
            if text:
                with open(file_path,'w') as f:
                    f.write(text)

            # Vérifie si le chemin est absolu
            if os.path.isabs(file_path):
                # Convertir en chemin relatif pour l'interface Jupyter
                # Racine de Jupyter (peut nécessiter une adaptation en fonction de votre configuration)
                jupyter_root = os.path.expanduser("~")
                relative_path = os.path.relpath(file_path, jupyter_root)
            else:
                relative_path = file_path

            # Ouvre le fichier dans un nouvel onglet du même serveur Jupyter
            display(Javascript(f'window.open("/notebooks/{relative_path}", "_blank");'))

        agent.add_tool(
            name="edit",
            obj=edit,
            description=dedent("""
            <<<self.instance_name>>>.edit(file=None,text=None)
            Opens a new notebook tab to let the user edit a file. 
            If no file is provided, opens a new buffer. 
            If text is provided, the text is written to the file/buffer before opening.
            """)
        )

    agent.add_tool(
        name="set_data_output",
        obj=agent.set_data_output,
        description=dedent("""
        <<<self.instance_name>>>.set_data_output(data)
        The user may call you programatically like so: data=<<<self.instance_name>>>(query,**kwargs). 
        This enables using you as an intelligent python function returning any kind of data. 
        When the user calls you in such a manner, your markdown output will be silenced and you're expected to run a script ending with a call to the set_data_output tool to set the result of the call with the appropriate data. 
        The kwargs of the call can be accessed via the <<<self.instance_name>>>.call_kwargs dict supporting attribute-style syntax. 
        This tool is purely internal to your functionning and is not meant to be used by the user.
        
        Example:
        User:
        data=<<<self.instance_name>>>("Return a list of n even numbers",n=5)
        
        Assistant:
        # No talking expected
        ```run_python
        <<<self.instance_name>>>.set_data_output([2*i for i in range(<<<self.instance_name>>>.call_kwargs.n)])
        ```
        #SUBMIT#           
        """
        )
    )

    def websearch(query,num=5,type='web',start=1,lasting=1):
        agent.observe(g_search(query,num=num,type=type,start=start),lasting=lasting)


    agent.add_tool(
        name='websearch',
        obj=websearch,
        description=dedent("""
        <<<self.instance_name>>>.websearch(query,num=5,type='web',start=1,lasting=1)
        Perform a google search. 
        type is either 'web' or 'image'. 
        Results are automatically observed in context (returns None).
        """)
    )

    agent.add_tool(
        name='webdriver',
        obj=get_webdriver,
        description=dedent("""
        driver=<<<self.instance_name>>>.webdriver()
        Spawns a preconfigured and ready to be used selenium headless firefox webdriver, suitable to work in the current environment. 
        You should always use this driver rather than attempting to configure one yourself.
        
        Example:
        # Spawn the webdriver
        driver = <<<self.instance_name>>>.webdriver()
        # Accès à la page d'accueil de Wikipédia
        driver.get('https://www.wikipedia.org/')
        # ...
        driver.quit()
        """)
    )

    agent.add_tool(
        name="observe",
        obj=agent.observe,
        description=dedent("""
        <<<self.instance_name>>>.observe(source,lasting=1)
        Your main tool to gain contextual awareness of some content. 
        Injects in you context feed textual data extracted from any kind of source (folder,file,url,variable,function,class,module...). 
        Allows you to 'look' at the content (this content will be visible to you only). 
        Observed content is short-lived in context, so you may have to reobserve the source in case you need the content again. 
        You may control the number of turns the content will last in context with the 'lasting' parameter.
        Depending on the source type the function will attempt to extract any possibly relevant info, even basic/mediocre.
        folder : get the recursive tree content.
        file : get the file content,
        url : get the text content extracted from the web page
        basic data type : a text representation of the content,
        object / function / class / module : a complete instrospection of the object
        ...
        """)
    )

    agent.add_tool(
        name="get_text",
        obj=get_text,
        description=dedent("""
        text_content=<<<self.instance_name>>>.get_text(source) 
        Extracts and returns textual data from any kind of source (folder,file,url,variable,function,class,module...). 
        Similar to <<<self.instance_name>>>.observe, but the text content is returned instead of being injected in context.
        folder : get the recursive tree content.
        file : get the file content as text (supported: pdf,doc,odt,xlsx,csv,ods,...),
        url : get the text content extracted from the web page
        basic data type : a text representation of the content,
        object / function / class / module : a complete instrospection of the object
        ...
        """)
    )

    agent.add_tool(
        name="document_store",
        obj=agent.store,
        description=dedent("""
        <<<self.instance_name>>>.document_store
        A document store used to implement your contextual data-retrieval mechanism.
        You will find automatically retrieved elements from the store (if any) as an actualized system message called 'Retrieval'. Use it to craft informed responses to the user.
        # Methods:
            <<<self.instance_name>>>.document_store.get_titles() # returns the list of titles of documents saved as files in the document store (can be loaded in memory).
            <<<self.instance_name>>>.document_store.get_loaded() # returns the list of titles of documents currently loaded in memory and active for chunk retrieval.
            <<<self.instance_name>>>.document_store.new_document(type,title,content,description) # (type='text' or 'json') Create a new stored document from a given content (either text or json_data, json_string, json_file) that is parsed, embedded and loaded for semantic search.
            <<<self.instance_name>>>.document_store.load_document(title) # Loads a document in memory.
            <<<self.instance_name>>>.document_store.close_document(title) # unloads a document from memory.
            <<<self.instance_name>>>.document_store.search(query,num=10) # returns most relevant pieces of informations found in the loaded documents related to a query.
            document= <<<self.instance_name>>>.document_store.get_document(title) # access the document object in the store
            document.search(query) # search in the document only
        # for a json document only:
            data=document['example']['key']['sequence'] # access data in the document
            document['example']['key']['sequence']=new_data # change data in the document
            document.dump() # save changes
        """)
    )

    agent.add_tool(
        name="open",
        obj=webbrowser.open,
        description=dedent("""
        <<<self.instance_name>>>.open(file_or_url) 
        Opens any file or url in a new tab of the user's default webbrowser. 
        Convenient way to open almost anything to show it to the user.
        """)
    )

    agent.add_tool(
        name="add_tool",
        obj=agent.add_tool,
        description=dedent("""
        <<<self.instance_name>>>.add_tool(name,obj,description)
        Adds a new tool the ai assistant, provided a name, an object/function as obj, and a complete description of how the tool should be used (signature, methods, example usage). 
        This tool will be accessible as <<<self.instance_name>>>.<tool_name> from the assistant instance.
        """)
    )

    agent.add_tool(
        name="memory",
        obj=agent.store.get_document("memory"),
        description=dedent("""
        <<<self.instance_name>>>.memory
        A special long term memory document (json type) from your document store, specially designed to enable lasting memory.
        Can be accessed and written to as a normal nested dict. Supports .dump() method so save changes and .search(query, num=10) for quick lookup.
        Contextually relevant memory entries will be automatically retrieved in context. Use explicit keys to organize data clearly and improve performance of semantic retrieval.
        """)
    )





