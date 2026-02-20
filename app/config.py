import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./provalab.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey_change_in_production_minimum_32_chars")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "7"))
HOTMART_WEBHOOK_TOKEN = os.getenv("HOTMART_WEBHOOK_TOKEN", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "nao-responda@provalab.com")
APP_BASE_URL = os.getenv("APP_BASE_URL", FRONTEND_URL)
HOTMART_CHECKOUT_URL = os.getenv("HOTMART_CHECKOUT_URL", "")
EMAIL_VERIFICATION_EXPIRATION_MINUTES = int(os.getenv("EMAIL_VERIFICATION_EXPIRATION_MINUTES", "10"))
EMAIL_VERIFICATION_MAX_ATTEMPTS = int(os.getenv("EMAIL_VERIFICATION_MAX_ATTEMPTS", "5"))
