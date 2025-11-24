TransFlow Backend Prototype

Este projeto é um protótipo de backend para gerenciar corridas urbanas, focado em processamento de dados em tempo real e assíncrono. Utiliza FastAPI para a API principal, MongoDB para persistência de dados de corrida, Redis para gerenciamento de saldo de motoristas (atômico) e RabbitMQ com FastStream para mensageria assíncrona.

Arquitetura

A arquitetura é baseada em microsserviços contêinerizados, orquestrados pelo Docker Compose:

- `api` (FastAPI/Uvicorn): servidor principal da API. Cadastra corridas e publica eventos.
- `consumer` (FastStream): worker assíncrono. Consome `corridas_finalizadas`, atualiza saldo no Redis e registra no MongoDB.
- `mongo` (MongoDB): banco de dados de corridas.
- `redis` (Redis): saldos dos motoristas (operações atômicas).
- `rabbitmq` (RabbitMQ): broker de mensagens.

A fila `corridas_finalizadas` é durável e as mensagens são publicadas com `delivery_mode=2` para persistência.

Endpoints principais:

- `GET /health` — status do Mongo e Redis.
- `GET /docs` — Swagger UI da API.
- `POST /corridas` — cria corrida e publica evento.
- `GET /corridas` — lista corridas.
- `GET /corridas/{forma_pagamento}` — filtra por pagamento.
- `GET /saldo/{motorista_nome}` — consulta saldo no Redis.

Passos de Instalação

Pré-requisitos: Docker e Docker Compose instalados.

Clone o repositório:

```
git clone [LINK DO SEU REPOSITÓRIO GITHUB AQUI]
cd transflow
```

Construir e iniciar os contêineres (API, consumer, Mongo, Redis, RabbitMQ):

```
docker-compose up --build -d
```

Verificar status dos serviços:

```
docker-compose ps
```

Ver logs (opcional):

```
docker logs p2-api-1 --follow
docker logs p2-consumer-1 --follow
```


Variáveis de Ambiente

As variáveis são definidas pelo `docker-compose.yml`:

- `MONGO_URI`: `mongodb://mongo:27017`
- `REDIS_HOST`: `redis`
- `REDIS_PORT`: `6379`
- `RABBITMQ_HOST`: `rabbitmq`

O `consumer` também aceita `RABBITMQ_URL`, `MONGO_URL`, `REDIS_URL`, mas monta automaticamente a partir das variáveis acima.

Instruções de Uso e Testes

A API estará acessível em `http://localhost:8000`. O Swagger em `http://localhost:8000/docs`.

1) Health check:

```
curl http://localhost:8000/health
```

2) Consultar saldo inicial (Redis):

```
curl http://localhost:8000/saldo/Carla
```

3) Cadastrar e processar corrida (MongoDB + RabbitMQ + Consumer):

Body de exemplo:

```
{
  "passageiro": { "nome": "Júlia", "telefone": "99999-2222" },
  "motorista": { "nome": "Carla", "nota": 4.9 },
  "origem": "Leblon",
  "destino": "Ipanema",
  "valor_corrida": 25.50,
  "forma_pagamento": "Cartao"
}
```

Publique usando o Swagger (`POST /corridas`).

Ver processamento no consumer:

```
docker logs p2-consumer-1 --follow
```

Consultar novo saldo:

```
curl http://localhost:8000/saldo/Carla
```

4) Consultar corridas (MongoDB):

- Listar todas: `GET /corridas`
- Filtrar por pagamento: `GET /corridas/Cartao`

Capturas de Tela

![Tela do sistema](screenshot.jpeg)

- Docker Compose status: `docs/prints/docker-ps.png`
- Swagger UI: `docs/prints/api-docs.png`
- Logs do consumer: `docs/prints/consumer-logs.png`

Como capturar:

- Windows: `Win + Shift + S` e salve em `docs/prints/`.
- Linux/macOS: use sua ferramenta de captura e salve no mesmo diretório.

Link do Repositório GitHub

[Insira o link do seu repositório GitHub público aqui]
