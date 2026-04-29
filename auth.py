import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from supabase import Client

JWT_SECRET = os.environ.get("JWT_SECRET", "fallback-dev-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_token(user_id: str, email: str, name: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def signup(supabase: Client, name: str, email: str, password: str) -> str | None:
    try:
        existing = supabase.table("users").select("id").eq("email", email).execute()
        if existing.data:
            return None
        pw_hash = hash_password(password)
        response = supabase.table("users").insert(
            {"name": name, "email": email, "password_hash": pw_hash}
        ).execute()
        user = response.data[0]
        return create_token(str(user["id"]), user["email"], user["name"])
    except Exception as e:
        print(f"Signup error: {e}")
        return None


def login(supabase: Client, email: str, password: str) -> str | None:
    try:
        response = supabase.table("users").select("*").eq("email", email).execute()
        if not response.data:
            return None
        user = response.data[0]
        if not verify_password(password, user["password_hash"]):
            return None
        return create_token(str(user["id"]), user["email"], user["name"])
    except Exception as e:
        print(f"Login error: {e}")
        return None


def get_current_user(session_state) -> dict | None:
    token = session_state.get("token")
    if not token:
        return None
    return decode_token(token)
