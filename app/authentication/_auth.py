from datetime import datetime, timedelta, timezone
import os

from app.authentication._user import User
from jose import jwt


def generate_jwt_token(user: User) -> str:
    """
    Gera um token JWT para o usuário autenticado.

    JWT (JSON Web Token) é como um "crachá digital":
    - Contém informações do usuário (payload)
    - É assinado com uma chave secreta (ninguém pode falsificar)
    - Tem prazo de validade (exp)
    - O servidor NÃO precisa guardar o token — só verifica a assinatura
    """

    # Lê quantos minutos o token vai durar (ex: 30 minutos)
    expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

    # Calcula o momento exato em que o token expira
    # timezone.utc garante que o horário seja UTC (padrão internacional)
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)

    # Payload = o conteúdo do token (informações que ficam "dentro" dele)
    # Qualquer pessoa com o token pode LER o payload — não coloque senhas aqui!
    payload = {
        "sub": user.email,  # "subject" — quem é o dono do token (convenção JWT)
        "name": user.name,  # dado extra para evitar consulta ao banco depois
        "exp": expire,  # "expiration" — quando o token deixa de ser válido
    }

    # jwt.encode() cria o token assinando o payload com a SECRET_KEY
    # Sem a SECRET_KEY correta, ninguém consegue criar um token válido
    token = jwt.encode(
        payload, os.getenv("SECRET_KEY"), algorithm=os.getenv("ALGORITHM")
    )
    return token
