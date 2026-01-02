from langchain.llms import Ollama
from app.config import OLLAMA_MODEL

def get_llm():
    """
    Returns a local Ollama-based LLM instance.
    Make sure Ollama is installed and running: https://ollama.ai
    Example: ollama run llama3
    """
    return Ollama(model=OLLAMA_MODEL)
