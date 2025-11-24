from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List
import os
import uuid
import redis
import json
from faststream.rabbit import RabbitBroker
from src.database.mongo_client import get_db

app = FastAPI(title="TransFlow API", version="1.0.0")

# Conexões
db = get_db()

# ✅ CONEXÃO REDIS CORRIGIDA para a versão 4.5.4
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=0,
    decode_responses=True  # Para retornar strings em vez de bytes
)

class Passageiro(BaseModel):
    nome: str
    telefone: str

class Motorista(BaseModel):
    nome: str
    nota: float

class CorridaCreate(BaseModel):
    passageiro: Passageiro
    motorista: Motorista
    origem: str
    destino: str
    valor_corrida: float
    forma_pagamento: str

class Corrida(CorridaCreate):
    id_corrida: str
    processada: bool = False
    saldo_atualizado: bool = False

RABBITMQ_URL = os.getenv("RABBITMQ_URL") or (
    lambda host: f"amqp://guest:guest@{host}:5672/"
)(os.getenv("RABBITMQ_HOST", "rabbitmq"))

broker = RabbitBroker(RABBITMQ_URL)

@app.on_event("startup")
async def start_broker():
    await broker.start()

@app.on_event("shutdown")
async def stop_broker():
    await broker.close()

async def publish_corrida_finalizada(corrida_data: dict):
    await broker.publish(corrida_data, queue="corridas_finalizadas")

@app.get("/", response_class=HTMLResponse)
async def homepage():
    return """
<!doctype html>
<html lang=pt-br>
<head>
<meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>TransFlow</title>
<style>
:root{--bg:#0f172a;--panel:#111827;--muted:#94a3b8;--text:#e5e7eb;--accent:#22c55e;--accent2:#3b82f6;--danger:#ef4444}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0b1220,#0f172a 40%,#0b1220);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica,Arial,sans-serif}
.container{max-width:1100px;margin:40px auto;padding:0 20px}
.header{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}
.title{font-weight:700;font-size:28px;letter-spacing:.3px}
.status{display:flex;gap:10px}
.badge{padding:6px 10px;border-radius:999px;background:#1f2937;color:#cbd5e1;font-size:12px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.card{background:rgba(17,24,39,.9);border:1px solid #1f2937;border-radius:14px;padding:16px;box-shadow:0 10px 30px rgba(0,0,0,.25)}
.card h3{margin:0 0 12px 0;font-size:16px}
.row{display:flex;gap:10px;margin-bottom:8px}
input,select{width:100%;padding:10px 12px;background:#0b1220;border:1px solid #1f2937;border-radius:10px;color:var(--text)}
button{padding:10px 12px;border:0;border-radius:10px;background:var(--accent2);color:#fff;cursor:pointer}
button.primary{background:var(--accent)}
button.danger{background:var(--danger)}
.list{max-height:240px;overflow:auto;border:1px solid #1f2937;border-radius:10px;padding:8px;background:#0b1220}
.item{padding:8px;border-bottom:1px solid #1f2937}
.item:last-child{border-bottom:0}
.muted{color:var(--muted);font-size:12px}
.footer{margin-top:24px;text-align:center;color:#9ca3af;font-size:12px}
</style>
</head>
<body>
<div class=container>
  <div class=header>
    <div class=title>TransFlow • Painel</div>
    <div class=status>
      <div id=badge-mongo class=badge>Mongo: ...</div>
      <div id=badge-redis class=badge>Redis: ...</div>
    </div>
  </div>

  <div class=grid>
    <div class=card>
      <h3>Criar Corrida</h3>
      <div class=row>
        <input id=p_nome placeholder="Passageiro: nome">
        <input id=p_tel placeholder="Passageiro: telefone">
      </div>
      <div class=row>
        <input id=m_nome placeholder="Motorista: nome">
        <input id=m_nota type=number step=0.1 min=0 max=5 placeholder="Motorista: nota">
      </div>
      <div class=row>
        <input id=origem placeholder="Origem">
        <input id=destino placeholder="Destino">
      </div>
      <div class=row>
        <input id=valor type=number step=0.01 min=0 placeholder="Valor da corrida">
        <select id=pag>
          <option>Cartao</option>
          <option>Pix</option>
          <option>Dinheiro</option>
        </select>
      </div>
      <div class=row>
        <button class=primary onclick="criar()">Publicar corrida</button>
        <div id=criar-msg class=muted></div>
      </div>
    </div>

    <div class=card>
      <h3>Consultar Saldo</h3>
      <div class=row>
        <input id=saldo-motorista placeholder="Motorista">
        <button onclick="consultarSaldo()">Consultar</button>
      </div>
      <div id=saldo-res class=list></div>
    </div>

    <div class=card>
      <h3>Corridas</h3>
      <div class=row>
        <button onclick="listar()">Listar todas</button>
        <select id=filtra-pag>
          <option value="">Filtrar por pagamento</option>
          <option>Cartao</option>
          <option>Pix</option>
          <option>Dinheiro</option>
        </select>
        <button onclick="filtrar()">Filtrar</button>
      </div>
      <div id=corridas class=list></div>
    </div>

    <div class=card>
      <h3>Health</h3>
      <div id=health class=list></div>
    </div>
  </div>

  <div class=footer>TransFlow ©</div>
</div>

<script>
const api=location.origin
async function atualizarHealth(){try{const r=await fetch(api+"/health");const j=await r.json();document.getElementById("health").innerHTML=JSON.stringify(j,null,2);document.getElementById("badge-mongo").textContent="Mongo: "+j.mongo;document.getElementById("badge-redis").textContent="Redis: "+j.redis}catch(e){document.getElementById("health").textContent="Erro ao consultar health"}}
async function criar(){const b={passageiro:{nome:document.getElementById("p_nome").value,telefone:document.getElementById("p_tel").value},motorista:{nome:document.getElementById("m_nome").value,nota:parseFloat(document.getElementById("m_nota").value||"0")},origem:document.getElementById("origem").value,destino:document.getElementById("destino").value,valor_corrida:parseFloat(document.getElementById("valor").value||"0"),forma_pagamento:document.getElementById("pag").value};const r=await fetch(api+"/corridas",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)});const j=await r.json();document.getElementById("criar-msg").textContent=r.ok?"Publicada: "+j.id_corrida:"Erro: "+(j.detail||r.status)}
async function consultarSaldo(){const m=document.getElementById("saldo-motorista").value;const r=await fetch(api+"/saldo/"+encodeURIComponent(m));const j=await r.json();document.getElementById("saldo-res").innerHTML=`<div class=item>${j.motorista}: ${j.saldo}</div>`}
async function listar(){const r=await fetch(api+"/corridas");const j=await r.json();renderCorridas(j)}
async function filtrar(){const f=document.getElementById("filtra-pag").value;if(!f){listar();return}const r=await fetch(api+"/corridas/"+encodeURIComponent(f));const j=await r.json();renderCorridas(j)}
function renderCorridas(arr){const el=document.getElementById("corridas");el.innerHTML="";arr.forEach(c=>{const d=document.createElement("div");d.className="item";d.textContent=`${c.id_corrida} • ${c.origem} → ${c.destino} • R$ ${c.valor_corrida} • ${c.forma_pagamento} • processada: ${c.processada}`;el.appendChild(d)})}
atualizarHealth();
</script>
</body>
</html>
"""

@app.post("/corridas", response_model=Corrida)
async def criar_corrida(corrida: CorridaCreate):
    """Cadastra uma nova corrida e publica evento"""
    try:
        corrida_dict = corrida.dict()
        corrida_dict["id_corrida"] = f"corrida_{uuid.uuid4().hex[:8]}"
        corrida_dict["processada"] = False
        corrida_dict["saldo_atualizado"] = False
        
        # Insere no MongoDB
        result = db.corridas.insert_one(corrida_dict)
        corrida_dict["_id"] = str(result.inserted_id)
        
        await publish_corrida_finalizada(corrida_dict)
        
        return corrida_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar corrida: {str(e)}")

@app.get("/corridas", response_model=List[Corrida])
async def listar_corridas():
    """Lista todas as corridas"""
    try:
        corridas = list(db.corridas.find())
        for corrida in corridas:
            corrida["_id"] = str(corrida["_id"])
        return corridas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar corridas: {str(e)}")

@app.get("/corridas/{forma_pagamento}", response_model=List[Corrida])
async def filtrar_corridas_por_pagamento(forma_pagamento: str):
    """Filtra corridas por forma de pagamento"""
    try:
        corridas = list(db.corridas.find({"forma_pagamento": forma_pagamento}))
        for corrida in corridas:
            corrida["_id"] = str(corrida["_id"])
        return corridas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao filtrar corridas: {str(e)}")

@app.get("/saldo/{motorista_nome}")
async def consultar_saldo(motorista_nome: str):
    """Consulta saldo do motorista no Redis"""
    try:
        saldo = redis_client.get(f"saldo:{motorista_nome}")
        if saldo is None:
            redis_client.set(f"saldo:{motorista_nome}", "0.0")
            saldo = "0.0"
        return {"motorista": motorista_nome, "saldo": float(saldo)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar saldo: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check do sistema"""
    try:
        db.client.admin.command('ping')
        mongo_status = "connected"
    except:
        mongo_status = "disconnected"

    try:
        # Testa conexão Redis
        redis_client.ping()
        redis_status = "connected"
    except:
        redis_status = "disconnected"

    return {
        "status": "healthy",
        "mongo": mongo_status,
        "redis": redis_status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
