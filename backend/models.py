from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"

class UserBase(BaseModel):
    email: str
    nome: str
    role: UserRole = UserRole.USER

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ClienteBase(BaseModel):
    nome: str
    cnpj: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    is_active: bool = True

class ClienteCreate(ClienteBase):
    pass

class Cliente(ClienteBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BalanceteBase(BaseModel):
    cliente_id: int
    mes: int
    ano: int
    receitas: float
    despesas: float
    lucro_bruto: float
    impostos: float
    lucro_liquido: float

class BalanceteCreate(BalanceteBase):
    pass

class Balancete(BalanceteBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class DashboardData(BaseModel):
    total_clientes: int
    total_receitas: float
    total_despesas: float
    lucro_total: float
    crescimento_mensal: float
    clientes_ativos: int

class FluxoCaixaData(BaseModel):
    mes: str
    receitas: float
    despesas: float
    saldo: float

class RelatorioBase(BaseModel):
    titulo: str
    tipo: str
    data_inicio: datetime
    data_fim: datetime
    cliente_id: Optional[int] = None

class RelatorioCreate(RelatorioBase):
    pass

class Relatorio(RelatorioBase):
    id: int
    created_at: datetime
    dados: dict

    class Config:
        from_attributes = True
