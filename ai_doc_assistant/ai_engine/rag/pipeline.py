from .retriever import DocumentRetriever
from .context_builder import ContextBuilder
from ai_engine.llm.chains import get_rag_chain, get_summary_chain, get_quiz_chain
from langchain_core.output_parsers import StrOutputParser

class RAGPipeline:
    def ask_question(self, question, document_id=None):
        docs = DocumentRetriever.retrieve_chunks(question, document_id)
        if not docs:
            return "No relevant context found in the document(s)."
            
        context = ContextBuilder.build_context(docs)
        
        chain = get_rag_chain() | StrOutputParser()
        answer = chain.invoke({"context": context, "question": question})
        return answer

    def summarize_document(self, parsed_text):
        text_to_summarize = parsed_text[:10000] if parsed_text else ""
        
        chain = get_summary_chain() | StrOutputParser()
        summary = chain.invoke({"text": text_to_summarize})
        return summary
        
    def generate_quiz(self, parsed_text):
        text_for_quiz = parsed_text[:15000] if parsed_text else ""
        
        chain = get_quiz_chain() | StrOutputParser()
        quiz = chain.invoke({"text": text_for_quiz})
        return quiz
