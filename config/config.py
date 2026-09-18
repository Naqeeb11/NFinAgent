import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Alpaca
    ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
    ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
    ALPACA_PAPER = os.getenv("ALPACA_PAPER", "true").lower() == "true"
    
    # Alpha Vantage
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

    # News API
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")

    # SEC Edgar
    # SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")
    SEC_COMPANY_NAME = os.getenv("SEC_COMPANY_NAME")
    SEC_CONTACT_EMAIL = os.getenv("SEC_CONTACT_EMAIL")
    
    # Ollama
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

config = Config()
