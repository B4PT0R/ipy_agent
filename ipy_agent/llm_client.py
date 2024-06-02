import litellm
import os

class LLMClient:

    """
    Class used to provide a unified LLM client interface for various providers.
    API keys can be provided either by a dict or via env variables
    """

    def __init__(self,model=None,api_keys=None):
        self.api_keys=api_keys or {}
        self.model=model
        self.init_api_keys()

    def init_api_keys(self,api_keys=None):
        if api_keys:
            for key,secret in api_keys.items():
                os.environ[key]=secret

    def chat_completion(self,model=None,**kwargs):
        model=model or self.model
        kwargs.update(model=model,messages=self.prepare_messages(kwargs['messages']))
        response=litellm.completion(**kwargs)
        return response.choices[0].message.content
        
    def streamed_completion(self,model=None,**kwargs):
        model=model or self.model
        kwargs.update(model=model,messages=self.prepare_messages(kwargs['messages']),stream=True)
        response=litellm.completion(**kwargs)
        for part in response:
            yield part.choices[0].delta.content or ""
        
    def prepare_messages(self,messages):
        prepared=[dict(content=msg.content,role=msg.role,name=msg.name) for msg in messages]
        return prepared
