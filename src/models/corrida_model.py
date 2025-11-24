from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4

# Modelo para o passageiro
class Passageiro(BaseModel):
    nome: str
    telefone: str

# Modelo para o motorista
class Motorista(BaseModel):
    nome: str
    nota: float = Field(..., ge=0, le=5) # Nota de 0 a 5

# Estrutura completa da corrida para entrada de dados (request body)
class CorridaCreate(BaseModel):
    passageiro: Passageiro
    motorista: Motorista
    origem: str
    destino: str
    valor_corrida: float = Field(..., gt=0) # Valor deve ser positivo
    forma_pagamento: str

# Estrutura completa da corrida para o MongoDB (inclui ID e status)
class CorridaDB(CorridaCreate):
    id_corrida: str = Field(default_factory=lambda: str(uuid4()))
    status: str = "PENDENTE_PROCESSAMENTO" # Status inicial

# Estrutura do evento a ser enviado para o RabbitMQ
class CorridaFinalizadaEvent(BaseModel):
    id_corrida: str
    motorista_nome: str
    valor_corrida: float