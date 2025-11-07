#!/usr/bin/env python3
"""
Teste manual do scraper com processo conhecido
"""
import sys
import asyncio
sys.path.append('/app/backend')

from scrapers.inpi_scraper import INPIScraper
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    # Conectar ao MongoDB
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client['test_database']
    
    # Criar scraper
    scraper = INPIScraper(db)
    
    # Processos de teste
    # 907206638 - sabemos que funciona
    # Vamos adicionar manualmente à coleção com esses números
    
    # Criar uma execução manual
    execucao_id = "manual-test-001"
    execucao = {
        "id": execucao_id,
        "data_execucao": "2025-11-07T20:40:00Z",
        "status": "processando",
        "xml_url": "manual",
        "total_processos": 1,
        "semana": 45,
        "ano": 2025,
        "mensagem_erro": None
    }
    
    await db.execucoes.insert_one(execucao)
    print("✅ Execução manual criada")
    
    # Processar apenas o 907206638
    print("\n🔍 Processando processo 907206638...")
    resultado = await scraper.processar_processo_com_pepi("907206638", execucao_id)
    
    print(f"\n📊 Resultado:")
    print(f"  Processo: {resultado.get('numero_processo')}")
    print(f"  MARCA: {resultado.get('marca')}")
    print(f"  EMAIL: {resultado.get('email')}")
    
    # Salvar no banco
    await db.processos_indeferimento.insert_one(resultado)
    print("\n✅ Processo salvo no banco de dados")
    
    # Atualizar status da execução
    await db.execucoes.update_one(
        {"id": execucao_id},
        {"$set": {"status": "concluido"}}
    )
    
    print("\n✨ Teste concluído!")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
