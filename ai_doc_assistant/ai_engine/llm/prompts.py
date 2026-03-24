from langchain.prompts import PromptTemplate

RAG_PROMPT_TEMPLATE = """You are a helpful Gen-AI Document Assistant.
Answer the question based only on the following context:
{context}

Question: {question}

If you don't know the answer based on the context, say "I don't have enough information to answer this based on the provided document." Do not guess.

Answer:"""

RAG_PROMPT = PromptTemplate(
    template=RAG_PROMPT_TEMPLATE,
    input_variables=["context", "question"]
)

SUMMARY_PROMPT_TEMPLATE = """Translate the following text into a clear, concise, and structured summary.
Highlight key points, main arguments, and conclusions.

Text: {text}

Summary:"""

SUMMARY_PROMPT = PromptTemplate(
    template=SUMMARY_PROMPT_TEMPLATE,
    input_variables=["text"]
)

QUIZ_PROMPT_TEMPLATE = """Based on the following document text, generate a quiz.
The quiz should include:
- 3 Multiple Choice Questions (with 4 options each and the correct answer indicated)
- 2 Conceptual/Short Answer Questions

Document Text:
{text}

Quiz:"""

QUIZ_PROMPT = PromptTemplate(
    template=QUIZ_PROMPT_TEMPLATE,
    input_variables=["text"]
)
