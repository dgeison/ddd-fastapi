import os

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

# OAuth2PasswordBearer instrui o FastAPI a:
# 1. Exigir o header: Authorization: Bearer <token>
# 2. Mostrar o botão "Authorize 🔒" no Swagger UI (/docs)
# 3. Extrair automaticamente o token desse header
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")


def get_email_from_token(
    token: str = Depends(_oauth2_scheme),  # FastAPI injeta o token automaticamente
) -> str:
    """
    Valida o token JWT e retorna o email do usuário.

    Usado como dependency em endpoints protegidos:
        @app.get("/me")
        def get_me(email: str = Depends(get_email_from_token)):
            ...
    """
    try:
        # jwt.decode() faz tudo de uma vez:
        # - verifica se a assinatura é válida (não foi adulterado)
        # - verifica se o token ainda não expirou (campo "exp")
        # - decodifica e retorna o payload
        payload = jwt.decode(
            token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")]
        )

        # Extrai o email do campo "sub" (subject) que colocamos ao criar o token
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=401, detail="Could not validate credentials"
            )
        return email

    except Exception:
        # Qualquer erro aqui (token expirado, assinatura inválida, formato errado)
        # deve retornar 401 — nunca expor detalhes do erro para o cliente
        raise HTTPException(status_code=401, detail="Could not validate credentials")
