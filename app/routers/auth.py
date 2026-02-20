import json
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.config import (
    EMAIL_VERIFICATION_EXPIRATION_MINUTES,
    EMAIL_VERIFICATION_MAX_ATTEMPTS,
    FRONTEND_URL,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)
from app.database import get_db
from app.models import EmailVerificationCode, Profile, User
from app.schemas import (
    EmailVerificationCheckRequest,
    EmailVerificationResponse,
    EmailVerificationSendRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.services.email_service import send_verification_code_email
from app.services.subscription_service import get_or_create_profile, initialize_trial

router = APIRouter(prefix="/auth", tags=["Autenticação"])

GOOGLE_STATE_TTL_SECONDS = 600
_google_state_cache: dict[str, float] = {}


def _cleanup_google_states() -> None:
    now = time.time()
    expired_keys = [
        state for state, created_at in _google_state_cache.items() if now - created_at > GOOGLE_STATE_TTL_SECONDS
    ]
    for state in expired_keys:
        _google_state_cache.pop(state, None)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_verification_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _exchange_google_code_for_tokens(code: str) -> dict:
    payload = urllib_parse.urlencode(
        {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": GOOGLE_REDIRECT_URI,
        }
    ).encode("utf-8")
    req = urllib_request.Request(
        "https://oauth2.googleapis.com/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_google_user_info(access_token: str) -> dict:
    req = urllib_request.Request(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    with urllib_request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


@router.post("/signup", response_model=TokenResponse)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """Registrar novo usuário."""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado",
        )

    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    profile = Profile(user_id=new_user.id, full_name=user_data.full_name)
    initialize_trial(profile)
    db.add(profile)
    db.commit()

    access_token = create_access_token(data={"sub": str(new_user.id)})
    return TokenResponse(access_token=access_token)


@router.post("/email/send-code", response_model=EmailVerificationResponse)
@router.post("/send-code", response_model=EmailVerificationResponse)
def send_email_verification_code(payload: EmailVerificationSendRequest, db: Session = Depends(get_db)):
    """Envia codigo de verificacao por e-mail."""
    email = _normalize_email(payload.email)
    purpose = (payload.purpose or "signup").strip().lower()

    if purpose == "signup":
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já cadastrado")

    db.query(EmailVerificationCode).filter(
        EmailVerificationCode.email == email,
        EmailVerificationCode.purpose == purpose,
        EmailVerificationCode.consumed_at.is_(None),
    ).update({EmailVerificationCode.consumed_at: datetime.utcnow()}, synchronize_session=False)

    code = _generate_verification_code()
    now = datetime.utcnow()
    record = EmailVerificationCode(
        email=email,
        purpose=purpose,
        code_hash=_hash_code(code),
        attempts=0,
        max_attempts=max(1, EMAIL_VERIFICATION_MAX_ATTEMPTS),
        verified=False,
        consumed_at=None,
        expires_at=now + timedelta(minutes=max(1, EMAIL_VERIFICATION_EXPIRATION_MINUTES)),
    )
    db.add(record)
    db.commit()

    sent = send_verification_code_email(email=email, code=code)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível enviar o código por e-mail",
        )

    return EmailVerificationResponse(success=True, message="Código enviado com sucesso")


@router.post("/email/verify-code", response_model=EmailVerificationResponse)
@router.post("/verify-code", response_model=EmailVerificationResponse)
def verify_email_code(payload: EmailVerificationCheckRequest, db: Session = Depends(get_db)):
    """Valida o codigo de verificacao enviado para o e-mail."""
    email = _normalize_email(payload.email)
    purpose = (payload.purpose or "signup").strip().lower()
    code = (payload.code or "").strip()

    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código inválido")

    record = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.purpose == purpose,
            EmailVerificationCode.consumed_at.is_(None),
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .first()
    )

    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum código pendente para este e-mail")
    if record.expires_at < datetime.utcnow():
        record.consumed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código expirado")
    if record.attempts >= record.max_attempts:
        record.consumed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Número máximo de tentativas excedido")

    if record.code_hash != _hash_code(code):
        record.attempts += 1
        if record.attempts >= record.max_attempts:
            record.consumed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código incorreto")

    record.verified = True
    record.consumed_at = datetime.utcnow()
    db.commit()
    return EmailVerificationResponse(success=True, message="Código verificado com sucesso")


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login com email e senha."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=access_token)


@router.get("/google/login")
def google_login():
    """Inicia fluxo OAuth com Google."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth não configurado no backend",
        )

    _cleanup_google_states()
    state = secrets.token_urlsafe(32)
    _google_state_cache[state] = time.time()

    query = urllib_parse.urlencode(
        {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{query}")


@router.get("/google/callback")
def google_callback(code: str | None = None, state: str | None = None, db: Session = Depends(get_db)):
    """Recebe callback OAuth e cria sessão local JWT."""
    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Callback OAuth inválido")

    _cleanup_google_states()
    if state not in _google_state_cache:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado OAuth inválido ou expirado")
    _google_state_cache.pop(state, None)

    try:
        token_response = _exchange_google_code_for_tokens(code)
        google_access_token = token_response.get("access_token")
        if not google_access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível obter token do Google")
        google_user = _fetch_google_user_info(google_access_token)
    except urllib_error.HTTPError as exc:
        detail = "Falha na autenticação com Google"
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            detail = payload.get("error_description") or payload.get("error") or detail
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
    except urllib_error.URLError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Erro de rede ao autenticar com Google") from exc

    email = google_user.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google não retornou email")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(48)),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        profile = Profile(user_id=user.id, full_name=google_user.get("name"), avatar_url=google_user.get("picture"))
        initialize_trial(profile)
        db.add(profile)
        db.commit()
    else:
        profile = get_or_create_profile(db, user)
        if profile:
            if google_user.get("name") and not profile.full_name:
                profile.full_name = google_user.get("name")
            if google_user.get("picture") and not profile.avatar_url:
                profile.avatar_url = google_user.get("picture")
            db.commit()

    access_token = create_access_token(data={"sub": str(user.id)})
    redirect_url = f"{FRONTEND_URL}/login?google_token={urllib_parse.quote(access_token)}"
    return RedirectResponse(url=redirect_url)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Obter dados do usuário autenticado."""
    return current_user
