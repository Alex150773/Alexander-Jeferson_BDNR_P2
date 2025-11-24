from faststream import FastStream
from faststream.rabbit import RabbitBroker
import os
import asyncio

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

broker = RabbitBroker(RABBITMQ_URL)
app = FastStream(broker)

async def publish_corrida_finalizada(corrida_data: dict):
    try:
        await broker.publish(
            corrida_data,
            queue="corridas_finalizadas"
        )
        print(f"✅ Evento publicado: {corrida_data['id_corrida']}")
        return True
    except Exception as e:
        print(f"❌ Erro ao publicar evento: {e}")
        return False

if __name__ == "__main__":
    async def test():
        await broker.start()
        print("✅ Producer conectado ao RabbitMQ")
        await broker.close()
    asyncio.run(test())
