import os
import requests
from fastapi import Header, HTTPException, Depends
from typing import Optional

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """Retrieves and validates the Supabase authenticated user using the Bearer JWT token."""
    if not authorization:
        # Guest user (no token provided)
        return None
        
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format. Must be Bearer <token>.")
    
    token = authorization.split(" ")[1]
    
    if SUPABASE_URL and SUPABASE_ANON_KEY:
        try:
            # Verify token using Supabase Auth endpoint
            url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/user"
            headers = {
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_ANON_KEY
            }
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                user_data = res.json()
                return {
                    "id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "display_name": user_data.get("user_metadata", {}).get("display_name")
                }
            else:
                raise HTTPException(status_code=401, detail="Invalid session token or token expired.")
        except HTTPException:
            raise
        except requests.exceptions.RequestException as e:
            print(f"[Auth] Supabase verification request failed: {e}")
            raise HTTPException(status_code=533, detail="Unable to verify session with Supabase Auth service.")
        except Exception as e:
            print(f"[Auth] Unexpected error: {e}")
            raise HTTPException(status_code=401, detail=str(e))
    
    # Fallback only when Supabase URL/key are not configured and REQUIRE_AUTH is false
    require_auth = os.getenv("REQUIRE_AUTH", "true").lower() == "true"
    if not require_auth:
        return {
            "id": "00000000-0000-0000-0000-000000000000",
            "email": "testing_guest@example.com",
            "display_name": "Testing Guest"
        }
        
    raise HTTPException(
        status_code=500,
        detail="Backend configuration error: SUPABASE_URL or SUPABASE_ANON_KEY is not defined in .env."
    )


def require_user(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Dependency that requires a user to be logged in (prevents guest access)."""
    require_auth = os.getenv("REQUIRE_AUTH", "true").lower() == "true"
    if not require_auth:
        # Return active user or fallback dummy guest
        return user or {
            "id": "00000000-0000-0000-0000-000000000000",
            "email": "testing_guest@example.com",
            "display_name": "Testing Guest"
        }

    if not user:
        raise HTTPException(status_code=401, detail="Authentication required for this operation.")
    return user
