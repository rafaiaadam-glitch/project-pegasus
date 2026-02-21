"""Auth: JWT tokens + Apple/Google OAuth verification."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

import bcrypt
import httpx
import jwt
from fastapi import Request


LOGGER = logging.getLogger("pegasus.auth")

JWT_SECRET_ENV = "PLC_JWT_SECRET"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30

# Cache Apple JWKS to avoid fetching on every request
_apple_jwks_cache: dict | None = None


def _get_jwt_secret() -> str:
    secret = os.getenv(JWT_SECRET_ENV, "").strip()
    if not secret:
        raise RuntimeError(f"{JWT_SECRET_ENV} environment variable must be set.")
    return secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_jwt(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> Dict[str, Any]:
    return jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Extract JWT from Authorization header and return user dict or None."""
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    try:
        payload = decode_jwt(token.strip())
        return {"id": payload["sub"], "email": payload["email"]}
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# =========================================================================
# Apple Sign-In verification
# =========================================================================

def _fetch_apple_jwks() -> dict:
    """Fetch Apple's public keys (JWKS) for verifying identity tokens."""
    global _apple_jwks_cache
    if _apple_jwks_cache is not None:
        return _apple_jwks_cache
    resp = httpx.get("https://appleid.apple.com/auth/keys", timeout=10)
    resp.raise_for_status()
    _apple_jwks_cache = resp.json()
    return _apple_jwks_cache


def verify_apple_token(identity_token: str) -> Dict[str, Any]:
    """Verify an Apple identity token (RS256 JWT) and return user info.

    Returns: { "email": str, "sub": str }
    Raises: ValueError on verification failure.
    """
    # Decode header to find the key ID
    try:
        unverified_header = jwt.get_unverified_header(identity_token)
    except jwt.DecodeError as exc:
        raise ValueError(f"Invalid Apple token format: {exc}") from exc

    kid = unverified_header.get("kid")
    if not kid:
        raise ValueError("Apple token missing 'kid' header.")

    # Fetch Apple's public keys and find the matching one
    jwks = _fetch_apple_jwks()
    matching_key = None
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            matching_key = key_data
            break

    if not matching_key:
        # Refresh cache in case Apple rotated keys
        global _apple_jwks_cache
        _apple_jwks_cache = None
        jwks = _fetch_apple_jwks()
        for key_data in jwks.get("keys", []):
            if key_data.get("kid") == kid:
                matching_key = key_data
                break

    if not matching_key:
        raise ValueError(f"No matching Apple public key for kid={kid}")

    # Build the public key and verify the token
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(matching_key)

    bundle_id = os.getenv("APPLE_BUNDLE_ID", "")
    try:
        payload = jwt.decode(
            identity_token,
            public_key,
            algorithms=["RS256"],
            audience=bundle_id if bundle_id else None,
            issuer="https://appleid.apple.com",
            options={"verify_aud": bool(bundle_id)},
        )
    except jwt.InvalidTokenError as exc:
        raise ValueError(f"Apple token verification failed: {exc}") from exc

    email = payload.get("email")
    sub = payload.get("sub")
    if not email or not sub:
        raise ValueError("Apple token missing email or sub claim.")

    return {"email": email, "sub": sub}


# =========================================================================
# Google Sign-In verification
# =========================================================================

def verify_google_token(id_token: str) -> Dict[str, Any]:
    """Verify a Google ID token via Google's tokeninfo endpoint.

    Returns: { "email": str, "sub": str, "name": str | None }
    Raises: ValueError on verification failure.
    """
    resp = httpx.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": id_token},
        timeout=10,
    )
    if resp.status_code != 200:
        raise ValueError(f"Google token verification failed: {resp.text}")

    data = resp.json()

    # Verify audience matches our client ID
    google_client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    if google_client_id and data.get("aud") != google_client_id:
        raise ValueError("Google token audience mismatch.")

    email = data.get("email")
    sub = data.get("sub")
    if not email or not sub:
        raise ValueError("Google token missing email or sub.")

    return {
        "email": email,
        "sub": sub,
        "name": data.get("name"),
    }
