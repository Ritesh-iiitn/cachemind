class ContextBuilder:
    @staticmethod
    def build_context(docs):
        context_texts = [doc.page_content for doc in docs]
        return "\n\n".join(context_texts)
