# environment, LLM client
# app/config.py
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

LTA_ACCOUNT_KEY = os.getenv("LTA_ACCOUNT_KEY")
if not LTA_ACCOUNT_KEY:
    raise ValueError("LTA_ACCOUNT_KEY is not set in the .env file")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in the .env file")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2,
)