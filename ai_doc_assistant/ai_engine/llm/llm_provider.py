import os
from django.conf import settings
from langchain_groq import ChatGroq

def get_llm(temperature=0.7):
    api_key = getattr(settings, 'GROQ_API_KEY', None) or os.getenv("GROQ_API_KEY")
    return ChatGroq(
        model="qwen/qwen3.6-27b",
        temperature=temperature,
        groq_api_key=api_key
    )


