from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_document(text:str):

    paragraphs = text.split("\n\n")

    chunks = []

    for paragraph in paragraphs:
        if len(paragraph) <= 1000:
            chunks.append(paragraph)
        else:
            chunks.extend(
                RecursiveCharacterTextSplitter(
                    separators=["\n\n", ". ", " ", ""],
                    chunk_size=1000,
                    chunk_overlap=100
                ).split_text(paragraph)
            )
    
    return chunks
    