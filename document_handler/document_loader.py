from langchain_docling.loader import DoclingLoader
import json

def load_document(path:str):
    loader = DoclingLoader(file_path=path)
    return loader.load()
    
    
if __name__ == "__main__":
    path = "../documents/small.txt"
    print(json.dumps(load_document(path)[0], indent=4, default=str))