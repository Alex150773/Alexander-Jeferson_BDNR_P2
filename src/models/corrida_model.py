from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4

class Passageiro(BaseModel):
    nome: str
    telefone: str

class Motorista(BaseModel):
    nome: str
    nota: float = Field(..., ge=0, le=5)

class CorridaCreate(BaseModel):
    passageiro: Passageiro
    motorista: Motorista
    origem: str
    destino: str
    valor_corrida: float = Field(..., gt=0)
    forma_pagamento: str

class CorridaDB(CorridaCreate):
    id_corrida: str = Field(default_factory=lambda: str(uuid4()))
    status: str = "PENDENTE_PROCESSAMENTO"

class CorridaFinalizadaEvent(BaseModel):
    id_corrida: str
    motorista_nome: str
    valor_corrida: float
