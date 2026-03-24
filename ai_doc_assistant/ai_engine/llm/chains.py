from langchain.chains import LLMChain
from .llm_provider import get_llm
from .prompts import RAG_PROMPT, SUMMARY_PROMPT, QUIZ_PROMPT

def get_rag_chain():
    llm = get_llm(temperature=0.0)
    return RAG_PROMPT | llm

def get_summary_chain():
    llm = get_llm(temperature=0.3)
    return SUMMARY_PROMPT | llm

def get_quiz_chain():
    llm = get_llm(temperature=0.5)
    return QUIZ_PROMPT | llm
