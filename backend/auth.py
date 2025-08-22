from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Exemplo simples de autenticação (ajuste conforme sua lógica real)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    # Aqui você pode validar o token e buscar o usuário no banco
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação inválido ou ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Retorne um dicionário de usuário fake para testes
    return {"user_id": "fake-user-id", "email": "user@example.com"}
