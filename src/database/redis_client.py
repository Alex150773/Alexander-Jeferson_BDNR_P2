from redis import asyncio as redis_async
import os
from typing import Optional

# Configuração do Redis
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

SALDO_KEY_PREFIX = "saldo:"

redis_client: Optional[redis_async.Redis] = None

async def connect_redis():
    """Inicializa conexão assíncrona com Redis usando aioredis."""
    global redis_client
    try:
        redis_client = redis_async.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}",
            decode_responses=True
        )

        await redis_client.ping()
        print("✅ Redis conectado com sucesso!")

        # Inicializa saldos
        await redis_client.setnx(f"{SALDO_KEY_PREFIX}Carla", 100.00)
        await redis_client.setnx(f"{SALDO_KEY_PREFIX}Joao", 200.00)

    except Exception as e:
        print(f"❌ Erro ao conectar ao Redis: {e}")

async def close_redis():
    """Fecha conexão."""
    global redis_client
    if redis_client:
        await redis_client.close()
        print("🔌 Redis desconectado.")

async def get_driver_balance(motorista_nome: str) -> float:
    """Retorna saldo atual."""
    if redis_client is None:
        raise ConnectionError("Redis não está inicializado.")

    key = f"{SALDO_KEY_PREFIX}{motorista_nome}"
    saldo_str = await redis_client.get(key)

    return float(saldo_str) if saldo_str else 0.0

async def atomically_increase_balance(motorista_nome: str, valor: float) -> float:
    """Incrementa saldo usando INCRBYFLOAT."""
    if redis_client is None:
        raise ConnectionError("Redis não está inicializado.")

    key = f"{SALDO_KEY_PREFIX}{motorista_nome}"
    return await redis_client.incrbyfloat(key, valor)
