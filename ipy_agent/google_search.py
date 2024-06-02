import os
_root_=os.path.dirname(os.path.abspath(__file__))
import sys
if not sys.path[0]==_root_:
    sys.path.insert(0,_root_)
def root_join(*args):
    return os.path.join(_root_,*args)

from googleapiclient.discovery import build

def subdict(original_dict, keys):
    return {k: original_dict[k] for k in keys if k in original_dict}

def google_search(api_key,cse_id,query,num=5, start=1, type='web'):
    service = build("customsearch", "v1", developerKey=api_key)
    ns = num // 10
    r = num % 10
    results = []
    if not ns == 0:
        for i in range(ns):
            args_dict = {
                'cx': cse_id,
                'q': query,
                'num': 10,
                'start': start + i * 10
            }
            if type == 'image':
                args_dict['searchType'] = 'image'
            res = service.cse().list(**args_dict).execute()
            for item in res['items']:
                results.append(subdict(item,["title","link","snippet"]))
    if not r == 0:
        args_dict = {
            'cx': cse_id,
            'q': query,
            'num': r,
            'start': start + ns * 10
        }
        if type == 'image':
            args_dict['searchType'] = 'image'
        res = service.cse().list(**args_dict).execute()
        for item in res['items']:
            results.append(subdict(item,["title","link","snippet"]))

    return results

def init_google_search(api_key=None,cse_id=None):
    api_key=api_key or os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
    cse_id=cse_id or os.getenv("GOOGLE_CUSTOM_SEARCH_CX")
    def g_search(query,num=5,start=1,type='web'):
        if api_key and cse_id:
            return google_search(api_key,cse_id,query,num=num,start=start,type=type)
        else:
            return None
    return g_search

