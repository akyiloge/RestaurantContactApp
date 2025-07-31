import os
from dotenv import load_dotenv

load_dotenv()

# Gmail API Configuration
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = 'gmail_credentials.json'
TOKEN_FILE = 'gmail_token.pickle'

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0

# Search Configuration
DEFAULT_MAX_RESULTS = 50
DEFAULT_EMAIL_LIMIT = 10