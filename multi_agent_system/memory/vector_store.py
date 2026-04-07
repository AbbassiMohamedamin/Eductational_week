import os
from typing import Any
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from config import FAISS_INDEX_PATH, EMBEDDING_MODEL

class VectorStore:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL
        )
        self.vector_store = None
        self.load()

    def add(self, text: str, metadata: dict[str, Any]):
        doc = Document(page_content=text, metadata=metadata)
        if self.vector_store is None:
            self.vector_store = FAISS.from_documents([doc], self.embeddings)
        else:
            self.vector_store.add_documents([doc])
        self.save()

    def query(self, text: str, k=3) -> list[dict[str, Any]]:
        if self.vector_store is None:
            return []
        
        docs = self.vector_store.similarity_search(text, k=k)
        return [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]

    def save(self):
        if self.vector_store:
            # Ensure directory exists
            os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)
            self.vector_store.save_local(FAISS_INDEX_PATH)

    def load(self):
        if os.path.exists(FAISS_INDEX_PATH):
            try:
                self.vector_store = FAISS.load_local(
                    FAISS_INDEX_PATH, 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                print(f"Error loading vector store: {e}")
                self.vector_store = None
        else:
            self.vector_store = None
