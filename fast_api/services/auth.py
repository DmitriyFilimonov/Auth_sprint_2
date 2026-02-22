import aiohttp
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config import settings

security = HTTPBearer()


async def authenticate_token(auth: HTTPAuthorizationCredentials = Security(security)):
    async with aiohttp.ClientSession() as session:
        try:
            url = f"http://{settings.auth_service_host}:{settings.auth_service_port}{settings.auth_service_authenticate_token_endpoint}"

            async with session.get(
                url, headers={"Authorization": f"Bearer {auth.credentials}"}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()

                raise HTTPException(status_code=401, detail="Unauthorized")
        except Exception:
            raise HTTPException(status_code=503, detail="Authorization service error")


async def check_admin_role(user: dict = Depends(authenticate_token)):
    print(user)

    if not user:
        return None

    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Только для админов")

    return user
