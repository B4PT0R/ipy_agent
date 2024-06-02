from openai import OpenAI
import numpy as np
import json
import os
from .utils import token_count

def normalize(vect,precision=5):
    inv_norm=1.0/np.linalg.norm(vect,ord=2)
    return [round(x_i*(inv_norm),precision) for x_i in vect]

def split_string(string, delimiters):
    """
    splits a string according to a chosen set of delimiters
    """
    substrings = []
    current_substring = ""
    i = 0
    while i < len(string):
        for delimiter in delimiters:
            if string[i:].startswith(delimiter):
                current_substring += delimiter
                if current_substring:
                    substrings.append(current_substring)
                    current_substring = ""
                i += len(delimiter)
                break
        else:
            current_substring += string[i]
            i += 1
    if current_substring:
        substrings.append(current_substring)
    return substrings

def split_text(text, max_tokens):
    """
    split a text into chunks of maximal token length, not breaking sentences in halves.
    """
    # Tokenize the text into sentences
    sentences = split_string(text,delimiters=["\n",". ", "! ", "? ", "... ", ": ", "; "])
    
    chunks = []
    current_chunk = ""
    current_token_count = 0
    
    for sentence in sentences:
        sentence_token_count = token_count(sentence)
        
        # If adding the next sentence exceeds the max_tokens limit,
        # save the current chunk and start a new one
        if current_token_count + sentence_token_count > max_tokens:
            chunks.append(current_chunk.strip())
            current_chunk = ""
            current_token_count = 0
        
        current_chunk += sentence
        current_token_count += sentence_token_count
    
    # Add the remaining chunk if it's not empty
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def flattener(data):
    if data is None:
        return []
    
    def _traverse(obj, keys, output):
        if isinstance(obj, dict):
            if not obj:
                output.append((keys, {}))  # Handle empty dict
            for k, v in obj.items():
                _traverse(v, keys + [k], output)
        elif isinstance(obj, list):
            if not obj:
                output.append((keys, []))  # Handle empty list
            for idx, item in enumerate(obj):
                _traverse(item, keys + [idx], output)
        else:
            output.append((keys, obj))

    output = []
    # Start with an empty tuple for the key sequence of the root object
    _traverse(data, [], output)
    # Handle single values and empty structures directly
    if not output:
        output.append(([], data))
    return output

def builder(flat_list):
    if not flat_list:
        return None

    # Handle single value case
    if len(flat_list) == 1 and len(flat_list[0][0]) == 0:
        return flat_list[0][1]

    # Determine the root type from the first key sequence if the flat list is not empty
    root = [] if flat_list and flat_list[0][0] and isinstance(flat_list[0][0][0], int) else {}
    
    for keys, value in flat_list:
        # Handle empty structure case
        if not keys:
            return value

        current_level = root
        for i, key in enumerate(keys):
            # If it's the last key in the sequence, set the value
            if i == len(keys) - 1:
                if isinstance(key, int):
                    # Ensure the current level is a list for integer keys
                    while len(current_level) <= key:
                        current_level.append(None)
                    current_level[key] = value
                else:
                    current_level[key] = value
            else:
                # Prepare next level structure
                if isinstance(key, int):
                    while len(current_level) <= key:
                        current_level.append({} if (i + 1 < len(keys) and not isinstance(keys[i + 1], int)) else [])
                    current_level = current_level[key]
                else:
                    if key not in current_level:
                        current_level[key] = {} if (i + 1 < len(keys) and not isinstance(keys[i + 1], int)) else []
                    current_level = current_level[key]
    return root

def is_in(keys,content):
    return any(is_prefix(keys,entry["keys"]) for entry in content.values())

def is_prefix(keys1,keys2):
    if len(keys1)==0:
        return True
    else:
        return keys2[:len(keys1)]==keys1

def to_str(data):
    if isinstance(data,str):
        return "'"+data+"'"
    else:
        return str(data)

def keys_as_str(keys):
    return ''.join(['['+to_str(key)+']' for key in keys])

def as_string(title,entry):
    return title+keys_as_str(entry[0])+"="+to_str(entry[1])

def subdict(original_dict, keys):
    return {k: original_dict[k] for k in keys if k in original_dict}

class Item:

    def __init__(self,document=None,keys=None):
        self.keys=keys
        self.document=document

    @property
    def content(self):
        content = {}
        for entry in self.document.data['content'].values():
            if is_prefix(self.keys,entry["keys"]):
                content[keys_as_str(entry["keys"])]=entry
        return content
    
    @property
    def value(self):
        # Reconstruct the nested substructure from the flat content
        flat_list = [(entry['keys'][len(self.keys):], entry['value']) for entry in self.content.values()]
        return builder(flat_list)
    
    def assign(self,value):
        self.document.set_value(self.keys,value)
    
    def __getitem__(self,key):
        keys=self.keys+[key]
        
        if is_in(keys,self.content):
            return Item(document=self.document, keys=keys)
        else:
            raise KeyError(f"Key {key} does not exist.")
    
    def __setitem__(self, key, value):
        # Construct the full key sequence for the new or updated value
        keys = self.keys + [key]
        self.document.set_value(keys, value)

    def __delitem__(self, key):
        keys = self.keys + [key]

        if is_in(keys,self.content):
            self.document.delete_value(keys)
        else:
            raise KeyError(f"Key {key} does not exist.")
        
    def __contains__(self,key):
        keys=self.keys+[key]
        return is_in(keys,self.content)

    def __repr__(self):
        return repr(self.value)
    
    def __str__(self):
        return str(self.value)
    
    def search(self,query,num=10,threshold=0.25):
        vect=self.document.store.embed([query],self.document.data['precision'],self.document.data['dimensions'])[0]
        results=[]
        for entry in self.content.values():
            results.append((entry["string"],np.dot(vect,entry["embedding"])))
        results.sort(key=lambda result: result[1], reverse=True)
        results=list(filter(lambda result:result[1]>=threshold,results))
        return results[:num]

class Document:

    def __init__(self,store,file=None):
        self.store=store
        self.file=file
        self.data=dict()

    def load(self,file=None):
        self.file=file or self.file
        if os.path.isfile(self.file) and file.endswith('.json'):
            with open(file) as f:
                self.data=json.load(f)

    def dump(self,file=None):
        self.file=file or self.file
        if self.file.endswith('.json'):
            with open(self.file,'w') as f:
                json.dump(self.data,f)

    def set_data(self,data):
        self.data=data



class JsonDocument(Item,Document):

    def __init__(self,store,file=None):
        Item.__init__(self,document=self,keys=[])
        Document.__init__(self,store,file)           

    def load_data(self,title,content,description,precision,dimensions):
        self.data=dict(
            title=title,
            type='json',
            description=description,
            precision=precision,
            dimensions=dimensions,
            content=dict()
        )
        if isinstance(content,str) and content.endswith(".json") and os.path.isfile(content):
            self.load_json_file(json_file=content)
        elif isinstance(content,str):
            self.load_json_string(json_string=content)
        else:
            self.load_json_data(content)

    def load_json_data(self,json_data):
        entries=flattener(json_data)
        strings=[as_string(self.data['title'],entry) for entry in entries]
        embeddings=self.store.embed(strings,self.data['precision'],self.data['dimensions'])
        for i in range(len(entries)):
            keys,value=entries[i]
            self.data['content'][keys_as_str(keys)]=dict(
                keys=keys,
                value=value,
                string=strings[i],
                embedding=embeddings[i]
            )

    def load_json_string(self,json_string):
        json_data=json.loads(json_string)
        self.load_json_data(json_data)

    def load_json_file(self,json_file):
        if os.path.isfile(json_file) and json_file.endswith('.json'):
            with open(json_file,'w') as f:
                json_data=json.load(f)
            self.load_json_data(json_data)

    def set_value(self, keys, value):

        if "" in self.data['content']:
            del self.data['content'][""]

        # Check and remove existing content (if any) under the specified keys
        self.delete_value(keys)

        # Prepare the string and embedding for the new value
        # If the value is structured, it is first converted to a flat list of entries
        if isinstance(value, dict) or isinstance(value, list):
            entries = [(keys+entry[0],entry[1]) for entry in flattener(value)]
            strings=[as_string(self.data['title'],entry) for entry in entries]
            embeddings=self.store.embed(strings,self.data['precision'],self.data['dimensions'])
            for i in range(len(entries)):
                keys,value=entries[i]
                self.data['content'][keys_as_str(keys)]=dict(
                    keys=keys,
                    value=value,
                    string=strings[i],
                    embedding=embeddings[i]
                )
        else:
            string = as_string(self.data['title'],(keys, value))
            embedding = self.store.embed([string],self.data['precision'],self.data['dimensions'])[0]
            self.data['content'][keys_as_str(keys)]=dict(
                keys= keys,
                value= value,
                string=string,
                embedding=embedding
            )

    def delete_value(self, keys):
        # Remove the entry or nested entries starting with the specified keys
        to_remove = [key for key in self.data['content'] if is_prefix(keys, key)]
        for key in to_remove:
            del self.data['content'][key]

class TextDocument(Document):

    def __init__(self,store,file=None,chunk_size=100):
        Document.__init__(self,store=store,file=file)
        self.chunk_size=chunk_size

    def load_data(self,title,content,description,precision,dimensions):
        self.data=dict(
            title=title,
            type='text',
            description=description,
            precision=precision,
            dimensions=dimensions,
            content=dict()
        )
        strings=split_text(content,self.chunk_size)
        embeddings=self.store.embed(strings,precision,dimensions)
        n=0
        for i in range(len(strings)):
            keys=[n+1,n+len(strings[i])]
            self.data['content'][str(keys)]=dict(keys=keys,string=strings[i],embedding=embeddings[i])
            n+=len(strings[i])

    def search(self,query,num=10,threshold=0.25):
        vect=self.store.embed([query],self.data['precision'],self.data['dimensions'])[0]
        results=[]
        for entry in self.data["content"].values():
            results.append((entry['string'],np.dot(vect,entry["embedding"])))
        results.sort(key=lambda result: result[1], reverse=True)
        results=list(filter(lambda result:result[1]>=threshold,results))
        return results[:num]

class DocumentStore:

    def __init__(self,openai_api_key=None,folder='./documents',dimensions=128,precision=5):
        self.openai_api_key=openai_api_key
        self.client=OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        self.dimensions=dimensions
        self.precision=precision
        self.folder=folder
        self.store={}
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

    def embed(self,strings,precision,dimensions):
        success=False
        while not success:
            try:
                response=self.client.embeddings.create(
                    input=strings,
                    model="text-embedding-3-small",
                    dimensions=dimensions
                )
            except Exception as e:
                print(str(e))
                success=False
            else:
                success=True
        embeddings=[normalize(response.data[i].embedding,precision) for i in range(len(strings))]
        return embeddings

    def get_loaded(self):
        return [dict(title=doc.data['title'],description=doc.data['description']) for doc in self.store.values()]
    
    def get_titles(self):
        return [os.path.basename(file).split('.')[0] for file in os.listdir(self.folder)]
    
    def save_document(self,title):
        if title in self.store:
            file=os.path.join(self.folder,f"{title}.json")
            self.store[title].dump()
            print(f"Successfully saved document '{title}' : path='{file}'")

    def get_document(self,title):
        if title in self.store:
            return self.store[title]
            
    def load_document(self,title):
        if title not in self.store:
            file=os.path.join(self.folder,f"{title}.json")
            if os.path.isfile(file):
                with open(file) as f:
                    data=json.load(f)
                if data['type']=='json':
                    doc=JsonDocument(store=self,file=file)
                elif data['type']=='text':
                    doc=TextDocument(store=self,file=file)
                doc.set_data(data)
                self.store[title]=doc
                print(f"Successfully loaded document '{title}' : path='{file}'")

    def close_document(self,title):
        if title in self.store:
            del self.store[title]
            print(f"Successfully closed document '{title}'")

    def new_document(self,type,title,content,description,precision=5,dimensions=128):
        file=os.path.join(self.folder,f"{title}.json")
        if type=='json':
            doc=JsonDocument(store=self,file=file)
        elif type=='text':
            doc=TextDocument(store=self,file=file)
        doc.load_data(title=title,content=content,description=description,precision=precision,dimensions=dimensions)
        self.store[title]=doc
        doc.dump()
        print(f"Successfully created document '{title}' : path='{file}'")

    def search(self,query,titles='all',num=10,threshold=0.35):
        if titles=='all':
            titles=self.store.keys()
        results={}
        for title in titles:
            results[title]=self.store[title].search(query,num=num,threshold=threshold)
        return results


if __name__=='__main__':

    data=dict(
        users=dict(
            Baptiste=dict(
                age=38,
                job="Programmer",
                city="Vibeuf",
                hobby="Guitar playing",
                email="bferrand.maths@gmail.com"
            ),
            Manon=dict(
                age=35,
                job="Nurse",
                city="Guignen",
                hobby="Going to the cinema.",
                email="manon.ferrand@laposte.net"
            )
        )
    )

    store=DocumentStore()

    #store.new_document(type='json',title="test",content=data,description="A test data structure.")
    store.load_document("test")
    doc=store.get_document('test')

    doc['users']['Aurélien']=dict(
        age=37,
        job="Cook",
        city="Rouen"
    )

    print(store.search("Dans quelle ville l'utilisateur Aurélien habite-t-il ?"))

    from get_text import get_text

    store.new_document(type='text',title="devin_townsend",description="Wikipédia article about Devin Townsend",content=get_text('./test.txt'))
    
    print(store.search("Où est né Devin Townsend ?"))









    





