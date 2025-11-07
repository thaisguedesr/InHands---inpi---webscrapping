from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from scrapers.inpi_scraper import INPIScraper
from scrapers.scheduler import start_scheduler, stop_scheduler

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Global scraper instance
scraper = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scraper
    scraper = INPIScraper(db)
    # Start scheduler on startup
    start_scheduler(scraper)
    logging.info("Scheduler iniciado - Execução toda terça-feira às 08:00")
    yield
    # Cleanup on shutdown
    stop_scheduler()
    client.close()

# Create the main app
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class Execucao(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data_execucao: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str  # 'processando', 'concluido', 'erro'
    xml_url: Optional[str] = None
    total_processos: int = 0
    semana: int
    ano: int
    mensagem_erro: Optional[str] = None

class ProcessoIndeferimento(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    execucao_id: str
    numero_processo: str
    marca: str
    email: Optional[str] = None
    data_extracao: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    semana: int
    ano: int

class ExecucaoResponse(BaseModel):
    execucao: Execucao
    processos: List[ProcessoIndeferimento]

# Routes
@api_router.get("/")
async def root():
    return {"message": "Sistema INPI Web Scraping - API Online"}

@api_router.post("/inpi/scrape")
async def trigger_scraping_manual(background_tasks: BackgroundTasks):
    """Trigger manual do scraping"""
    if scraper is None:
        raise HTTPException(status_code=500, detail="Scraper não inicializado")
    
    # Execute em background
    background_tasks.add_task(scraper.executar_scraping)
    
    return {
        "message": "Scraping iniciado em background",
        "status": "processando"
    }

@api_router.get("/inpi/executions", response_model=List[Execucao])
async def listar_execucoes():
    """Lista todas as execuções ordenadas por data (mais recente primeiro)"""
    execucoes = await db.execucoes.find({}, {"_id": 0}).sort("data_execucao", -1).to_list(1000)
    
    for exec in execucoes:
        if isinstance(exec.get('data_execucao'), str):
            exec['data_execucao'] = datetime.fromisoformat(exec['data_execucao'])
    
    return execucoes

@api_router.get("/inpi/executions/{execucao_id}", response_model=ExecucaoResponse)
async def obter_detalhes_execucao(execucao_id: str):
    """Obtém detalhes de uma execução específica com seus processos"""
    execucao = await db.execucoes.find_one({"id": execucao_id}, {"_id": 0})
    if not execucao:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    
    if isinstance(execucao.get('data_execucao'), str):
        execucao['data_execucao'] = datetime.fromisoformat(execucao['data_execucao'])
    
    processos = await db.processos_indeferimento.find(
        {"execucao_id": execucao_id}, 
        {"_id": 0}
    ).to_list(10000)
    
    for proc in processos:
        if isinstance(proc.get('data_extracao'), str):
            proc['data_extracao'] = datetime.fromisoformat(proc['data_extracao'])
    
    return {
        "execucao": execucao,
        "processos": processos
    }

@api_router.get("/inpi/executions/{execucao_id}/xlsx")
async def download_xlsx(execucao_id: str):
    """Download da planilha XLSX de uma execução"""
    execucao = await db.execucoes.find_one({"id": execucao_id}, {"_id": 0})
    if not execucao:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    
    processos = await db.processos_indeferimento.find(
        {"execucao_id": execucao_id}, 
        {"_id": 0}
    ).to_list(10000)
    
    if not processos:
        raise HTTPException(status_code=404, detail="Nenhum processo encontrado para esta execução")
    
    # Gerar XLSX
    from scrapers.xlsx_generator import gerar_xlsx
    xlsx_buffer = gerar_xlsx(processos, execucao)
    
    # Preparar resposta
    xlsx_buffer.seek(0)
    filename = f"inpi_indeferimentos_semana{execucao['semana']}_{execucao['ano']}.xlsx"
    
    return StreamingResponse(
        xlsx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/inpi/status")
async def obter_status():
    """Obtém status atual do sistema"""
    # Busca última execução
    ultima_execucao = await db.execucoes.find_one(
        {}, 
        {"_id": 0},
        sort=[("data_execucao", -1)]
    )
    
    total_processos = await db.processos_indeferimento.count_documents({})
    
    return {
        "sistema_online": True,
        "ultima_execucao": ultima_execucao,
        "total_processos_banco": total_processos,
        "proxima_execucao": "Terça-feira às 08:00 (horário Brasil)"
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)