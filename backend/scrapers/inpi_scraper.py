import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Optional
import uuid
from .xml_parser import parsear_xml_revista
from .email_notifier import enviar_email_notificacao

logger = logging.getLogger(__name__)

class INPIScraper:
    def __init__(self, db):
        self.db = db
        self.base_url = "https://revistas.inpi.gov.br/rpi/"
    
    async def buscar_ultimo_xml_marcas(self) -> Optional[str]:
        """Busca URL do último XML da seção de marcas"""
        try:
            logger.info(f"Buscando revista em {self.base_url}")
            response = requests.get(self.base_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Procurar link do XML de marcas (última edição)
            # Normalmente é algo como: "Marca - Download XML"
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text().strip().lower()
                
                # Buscar link que contenha 'marca' e 'xml'
                if 'marca' in text and 'xml' in href.lower():
                    xml_url = href if href.startswith('http') else f"{self.base_url.rstrip('/')}/{href.lstrip('/')}"
                    logger.info(f"XML encontrado: {xml_url}")
                    return xml_url
            
            # Se não encontrar pela descrição, buscar diretamente arquivo .xml
            for link in links:
                href = link.get('href', '')
                if 'marca' in href.lower() and href.endswith('.xml'):
                    xml_url = href if href.startswith('http') else f"{self.base_url.rstrip('/')}/{href.lstrip('/')}"
                    logger.info(f"XML encontrado (direto): {xml_url}")
                    return xml_url
            
            logger.warning("Nenhum XML de marcas encontrado")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar XML: {str(e)}")
            return None
    
    async def baixar_xml(self, url: str) -> Optional[str]:
        """Baixa o conteúdo XML"""
        try:
            logger.info(f"Baixando XML de {url}")
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            logger.info(f"XML baixado com sucesso - {len(response.content)} bytes")
            return response.text
        except Exception as e:
            logger.error(f"Erro ao baixar XML: {str(e)}")
            return None
    
    async def executar_scraping(self):
        """Executa o processo completo de scraping"""
        execucao_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        semana = now.isocalendar()[1]
        ano = now.year
        
        logger.info(f"Iniciando scraping - Execução ID: {execucao_id}")
        
        # Criar registro de execução
        execucao = {
            "id": execucao_id,
            "data_execucao": now.isoformat(),
            "status": "processando",
            "xml_url": None,
            "total_processos": 0,
            "semana": semana,
            "ano": ano,
            "mensagem_erro": None
        }
        await self.db.execucoes.insert_one(execucao)
        
        try:
            # 1. Buscar URL do XML
            xml_url = await self.buscar_ultimo_xml_marcas()
            if not xml_url:
                raise Exception("XML não encontrado na página da revista")
            
            # Atualizar URL
            await self.db.execucoes.update_one(
                {"id": execucao_id},
                {"$set": {"xml_url": xml_url}}
            )
            
            # 2. Baixar XML
            xml_content = await self.baixar_xml(xml_url)
            if not xml_content:
                raise Exception("Falha ao baixar XML")
            
            # Enviar email de notificação
            enviar_email_notificacao(
                assunto="✅ Revista INPI baixada com sucesso",
                corpo=f"""A revista INPI foi baixada com sucesso!
                
Data: {now.strftime('%d/%m/%Y %H:%M:%S')}
Semana: {semana}/{ano}
URL: {xml_url}
                
Processando dados..."""
            )
            
            # 3. Parsear XML e extrair processos de indeferimento
            processos = parsear_xml_revista(xml_content, execucao_id, semana, ano)
            
            logger.info(f"Encontrados {len(processos)} processos de indeferimento")
            
            # 4. Salvar processos no banco
            if processos:
                processos_dict = [p.dict() if hasattr(p, 'dict') else p for p in processos]
                for proc in processos_dict:
                    if 'data_extracao' in proc and isinstance(proc['data_extracao'], datetime):
                        proc['data_extracao'] = proc['data_extracao'].isoformat()
                
                await self.db.processos_indeferimento.insert_many(processos_dict)
            
            # 5. Atualizar execução como concluída
            await self.db.execucoes.update_one(
                {"id": execucao_id},
                {"$set": {
                    "status": "concluido",
                    "total_processos": len(processos)
                }}
            )
            
            logger.info(f"Scraping concluído com sucesso - {len(processos)} processos salvos")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Erro durante scraping: {error_msg}")
            
            # Atualizar execução com erro
            await self.db.execucoes.update_one(
                {"id": execucao_id},
                {"$set": {
                    "status": "erro",
                    "mensagem_erro": error_msg
                }}
            )
            
            # Enviar email de erro
            enviar_email_notificacao(
                assunto="❌ Erro no scraping INPI",
                corpo=f"""Erro ao executar scraping da revista INPI.
                
Data: {now.strftime('%d/%m/%Y %H:%M:%S')}
Erro: {error_msg}"""
            )