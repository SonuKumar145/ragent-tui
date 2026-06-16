import json

def print_ok_string_message(_id:str, message:str, end:str=None, **extras:dict):
    print(json.dumps({
        'id':_id,
        'message': message,
        'status':"ok",
        **extras
    }), end=end, flush=True)

def print_inprocess_string_message(_id:str, message:str, end:str=None, **extras:dict):
    print(json.dumps({
        'id':_id,
        'message':message,
        'status':"in_process",
        **extras
    }), end=end, flush=True)

def print_done_string_message(_id:str, message:str, end:str=None, **extras:dict):
    print(json.dumps({
        'id':_id,
        'message':message,
        'status':"done",
        **extras
    }), end=end, flush=True)
        
def print_warning_string_message(_id:str, message:str, **extras:dict):
    print(json.dumps({
        'id':_id,
        'warning':message,
        'status':"warning",
        **extras
    }), flush=True)
    
def print_error_string_message(_id:str, error_message:str, _raise=False , **extras:dict):
    print(json.dumps({
        'id':_id,
        'error':error_message,
        'status':"error",
        **extras
    }), flush=True)
    
    if _raise:
        raise Exception(error_message)