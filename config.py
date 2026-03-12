import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Resend
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
DIGEST_TO_EMAIL = os.getenv("DIGEST_TO_EMAIL", "")
DIGEST_FROM_EMAIL = os.getenv("DIGEST_FROM_EMAIL", "digest@yourdomain.com")

# Apify (Twitter scraping)
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")

# App
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "5000"))
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
