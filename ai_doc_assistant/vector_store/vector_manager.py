import os
from pathlib import Path
from langchain_community.vectorstores import FAISS
from ai_engine.embeddings.embedder import get_embeddings

VECTOR_STORE_PATH = Path(__file__).resolve().parent / "faiss_index"

class VectorManager:
    def __init__(self):
        self.embeddings = get_embeddings()
        self.index_name = "doc_index"
        
    def _get_index_path(self):
        return os.path.join(VECTOR_STORE_PATH, self.index_name)

    def add_texts(self, texts, metadatas=None):
        if not texts:
            return
            
        index_path = self._get_index_path()
        if os.path.exists(index_path):
            vectorstore = FAISS.load_local(index_path, self.embeddings, allow_dangerous_deserialization=True)
            vectorstore.add_texts(texts=texts, metadatas=metadatas)
        else:
            vectorstore = FAISS.from_texts(texts=texts, embedding=self.embeddings, metadatas=metadatas)
            
        if not os.path.exists(VECTOR_STORE_PATH):
            os.makedirs(VECTOR_STORE_PATH)
            
        vectorstore.save_local(index_path)
        
    def similarity_search(self, query, k=5, filter=None):
        index_path = self._get_index_path()
        if not os.path.exists(index_path):
            return []
            
        vectorstore = FAISS.load_local(index_path, self.embeddings, allow_dangerous_deserialization=True)
        
        # In langchain FAISS, filter is an dict, so it expects exact match metadata filtering.
        if filter:
            docs = vectorstore.similarity_search(query, k=k, filter=filter)
        else:
            docs = vectorstore.similarity_search(query, k=k)
        return docs
