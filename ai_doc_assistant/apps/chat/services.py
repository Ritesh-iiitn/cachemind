from ai_engine.rag.pipeline import RAGPipeline

class ChatService:
    @staticmethod
    def answer_question(question, document_id=None):
        pipeline = RAGPipeline()
        answer = pipeline.ask_question(question, document_id)
        return answer
