import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Optional
import uuid
import zipfile
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor
from .xml_parser import parsear_xml_revista
from .email_notifier import enviar_email_notificacao
from .pepi_scraper import PepiScraper

logger = logging.getLogger(__name__)

class INPIScraper:
    def __init__(self, db):
        self.db = db
        self.base_url = "https://revistas.inpi.gov.br/rpi/"
    
    async def buscar_ultimo_xml_marcas(self) -> Optional[tuple]:
        """Busca URL do último XML da seção de marcas
        Retorna: (xml_url, numero_revista)
        """
        try:
            logger.info(f"Buscando revista em {self.base_url}")
            response = requests.get(self.base_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Encontrar primeira linha da tabela (última edição)
            # Formato do link: https://revistas.inpi.gov.br/txt/RM{NUMERO}.zip
            table = soup.find('table')
            if not table:
                logger.error("Tabela de revistas não encontrada")
                return None
            
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) > 0:
                    # Primeira coluna: número da revista
                    numero_revista = cols[0].get_text().strip()
                    
                    # Buscar link XML na coluna de Marcas (coluna 6)
                    if len(cols) >= 7:
                        marcas_col = cols[6]  # Coluna "SEÇÃO V - MARCAS"
                        xml_link = marcas_col.find('a', string='XML')
                        
                        if xml_link and xml_link.get('href'):
                            xml_url = xml_link.get('href')
                            if not xml_url.startswith('http'):
                                xml_url = f"https://revistas.inpi.gov.br/{xml_url.lstrip('/')}"
                            
                            logger.info(f"XML encontrado: {xml_url} (Revista {numero_revista})")
                            return (xml_url, numero_revista)
            
            logger.warning("Nenhum XML de marcas encontrado na primeira edição")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar XML: {str(e)}")
            return None
    
    async def baixar_xml(self, url: str) -> Optional[str]:
        """Baixa e extrai o conteúdo XML do arquivo ZIP"""
        try:
            logger.info(f"Baixando arquivo ZIP de {url}")
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            logger.info(f"ZIP baixado com sucesso - {len(response.content)} bytes")
            
            # Extrair XML do ZIP
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                # Listar arquivos no ZIP
                file_list = zip_file.namelist()
                logger.info(f"Arquivos no ZIP: {file_list}")
                
                # Buscar arquivo XML
                xml_file = None
                for filename in file_list:
                    if filename.lower().endswith('.xml'):
                        xml_file = filename
                        break
                
                if not xml_file:
                    logger.error("Nenhum arquivo XML encontrado no ZIP")
                    return None
                
                # Ler conteúdo do XML
                with zip_file.open(xml_file) as xml_content:
                    xml_text = xml_content.read().decode('utf-8')
                    logger.info(f"XML extraído com sucesso - {len(xml_text)} bytes")
                    return xml_text
            
        except Exception as e:
            logger.error(f"Erro ao baixar/extrair XML: {str(e)}")
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
            result = await self.buscar_ultimo_xml_marcas()
            if not result:
                raise Exception("XML não encontrado na página da revista")
            
            xml_url, numero_revista = result
            
            # Atualizar URL
            await self.db.execucoes.update_one(
                {"id": execucao_id},
                {"$set": {"xml_url": xml_url}}
            )
            
            # 2. Baixar e extrair XML do ZIP
            xml_content = await self.baixar_xml(xml_url)
            if not xml_content:
                raise Exception("Falha ao baixar/extrair XML")
            
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
            
            logger.info(f"Encontrados {len(processos)} processos de indeferimento no total")
            
            # Filtrar apenas processos SEM procurador
            processos_sem_procurador = [p for p in processos if not p.get('tem_procurador', False)]
            processos_com_procurador = [p for p in processos if p.get('tem_procurador', False)]
            
            logger.info(f"   ✅ Com procurador: {len(processos_com_procurador)} (serão ignorados)")
            logger.info(f"   ❌ Sem procurador: {len(processos_sem_procurador)} (serão processados)")
            logger.info("Iniciando busca de emails no pePI...")
            
            # 4. Buscar emails no pePI apenas para processos SEM procurador
            pepi_scraper = PepiScraper()
            
            # Processar em lotes para não sobrecarregar
            lote_size = 10
            total_com_email = 0
            
            for i in range(0, len(processos_sem_procurador), lote_size):
                lote = processos_sem_procurador[i:i+lote_size]
                logger.info(f"Processando lote {i//lote_size + 1}/{(len(processos_sem_procurador)//lote_size) + 1}")
                
                # Executar em paralelo (ThreadPoolExecutor para código síncrono)
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = []
                    for proc in lote:
                        future = executor.submit(
                            pepi_scraper.buscar_processo_e_extrair_email,
                            proc['numero_processo']
                        )
                        futures.append((proc, future))
                    
                    # Coletar resultados
                    for proc, future in futures:
                        try:
                            email = future.result(timeout=60)
                            if email:
                                proc['email'] = email
                                total_com_email += 1
                        except Exception as e:
                            logger.error(f"Erro ao processar {proc['numero_processo']}: {str(e)}")
                
                # Pequeno delay entre lotes
                await asyncio.sleep(2)
            
            logger.info(f"Total de processos com email extraído: {total_com_email}/{len(processos_sem_procurador)}")
            
            # 5. Salvar apenas processos SEM procurador no banco
            if processos_sem_procurador:
                processos_dict = [p.dict() if hasattr(p, 'dict') else p for p in processos_sem_procurador]
                for proc in processos_dict:
                    if 'data_extracao' in proc and isinstance(proc['data_extracao'], datetime):
                        proc['data_extracao'] = proc['data_extracao'].isoformat()
                
                await self.db.processos_indeferimento.insert_many(processos_dict)
            
            # 6. Atualizar execução como concluída
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