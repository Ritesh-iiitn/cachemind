import os
from langchain_groq import ChatGroq

def get_llm(temperature=0.7):
    return ChatGroq(
        model="llama-3.3-70b-versatile",  # Can be changed to other Groq models like mixtral-8x7b-32768
        temperature=temperature,
        groq_api_key=os.getenv("GROQ_API_KEY")
    )
