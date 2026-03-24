from vector_store.vector_manager import VectorManager

class DocumentRetriever:
    @staticmethod
    def retrieve_chunks(query, document_id=None, top_k=5):
        vector_manager = VectorManager()
        filter_dict = {"document_id": str(document_id)} if document_id else None
        docs = vector_manager.similarity_search(query, k=top_k, filter=filter_dict)
        return docs
