from faststream import FastStream
from faststream.rabbit import RabbitBroker
import os
import json
from pymongo import MongoClient
import redis
import time
import asyncio
RABBITMQ_URL = os.getenv("RABBITMQ_URL") or (
    lambda host: f"amqp://guest:guest@{host}:5672/"
)(os.getenv("RABBITMQ_HOST", "rabbitmq"))

MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGO_URI") or "mongodb://mongo:27017"

REDIS_URL = os.getenv("REDIS_URL") or (
    lambda host, port: f"redis://{host}:{port}"
)(os.getenv("REDIS_HOST", "redis"), os.getenv("REDIS_PORT", "6379"))

try:
    broker = RabbitBroker(RABBITMQ_URL, prefetch_count=1)
except TypeError:
    broker = RabbitBroker(RABBITMQ_URL)

app = FastStream(broker)

def connect_with_retry(connection_func, name, max_retries=5):
    for attempt in range(max_retries):
        try:
            print(f"📡 Conectando ao {name}... (tentativa {attempt + 1}/{max_retries})")
            return connection_func()
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"⏳ Falha na conexão ({name}): {e}. Aguardando {wait_time}s antes de tentar novamente...")
                time.sleep(wait_time)
            else:
                print(f"❌ Falha ao conectar ao {name} após {max_retries} tentativas: {e}")
                raise

mongo_client = connect_with_retry(lambda: MongoClient(MONGO_URL), "MongoDB")
db = mongo_client.transflow
redis_client = connect_with_retry(lambda: redis.from_url(REDIS_URL, decode_responses=True), "Redis")

@broker.subscriber("corridas_finalizadas")
async def processar_corrida_finalizada(corrida_data: dict):
   
    try:
        if isinstance(corrida_data, (bytes, str)):
            try:
                corrida_data = json.loads(corrida_data if isinstance(corrida_data, str) else corrida_data.decode("utf-8"))
            except Exception:
                corrida_data = {"raw": str(corrida_data)}
        print(f"🔄 Processando corrida: {corrida_data.get('id_corrida')}")
        
        motorista = corrida_data.get('motorista', {})
        motorista_id = motorista.get('id') or motorista.get('cpf') or motorista.get('nome')
        motorista_key = f"saldo:{motorista_id}"
        valor_corrida = float(corrida_data.get('valor_corrida', 0.0))
        id_corrida = corrida_data.get('id_corrida')
        
        def redis_update():
            try:
                return redis_client.incrbyfloat(motorista_key, valor_corrida)
            except AttributeError:
                with redis_client.pipeline() as pipe:
                    while True:
                        try:
                            pipe.watch(motorista_key)
                            saldo_atual = float(pipe.get(motorista_key) or "0.0")
                            novo_saldo = saldo_atual + valor_corrida
                            pipe.multi()
                            pipe.set(motorista_key, str(novo_saldo))
                            pipe.execute()
                            return novo_saldo
                        except redis.WatchError:
                            continue

        novo_saldo = await asyncio.to_thread(redis_update)
        print(f"💰 Saldo atualizado: {motorista_key} = {novo_saldo}")
        
        def mongo_update():
            return db.corridas.update_one(
                {"id_corrida": id_corrida},
                {"$set": {"processada": True, "saldo_atualizado": True, "ultimo_saldo": novo_saldo}},
                upsert=True
            )
        
        await asyncio.to_thread(mongo_update)
        print(f"✅ Corrida {id_corrida} processada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao processar corrida: {e}")


if __name__ == "__main__":
    import asyncio
    print("🚀 Iniciando consumer FastStream...")
    asyncio.run(app.run())
