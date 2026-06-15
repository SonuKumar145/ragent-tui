from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_document(text:str, chunk_size=1000, chunk_overlap=100)-> list[str]:

    paragraphs = text.split("\n\n")

    chunks = []

    for paragraph in paragraphs:
        if len(paragraph) <= 1000:
            chunks.append(paragraph)
        else:
            chunks.extend(
                RecursiveCharacterTextSplitter(
                    separators=["\n\n", ". ", " ", ""],
                    chunk_size = chunk_size,
                    chunk_overlap = chunk_overlap
                ).split_text(paragraph)
            )
    
    return chunks
    