from bs4 import BeautifulSoup
from datetime import datetime, timezone
import logging
import uuid

logger = logging.getLogger(__name__)

def parsear_xml_revista(xml_content: str, execucao_id: str, semana: int, ano: int) -> list:
    """Parse do XML da revista e extração de processos de indeferimento"""
    processos = []
    
    try:
        soup = BeautifulSoup(xml_content, 'lxml-xml')
        
        # Buscar todos os despachos com código IPAS024 (Indeferimento do pedido)
        despachos = soup.find_all('despacho', {'codigo': 'IPAS024'})
        
        logger.info(f"Encontrados {len(despachos)} despachos de indeferimento")
        
        for despacho in despachos:
            try:
                # Navegar até o processo pai
                processo_tag = despacho.find_parent('processo')
                if not processo_tag:
                    continue
                
                # Extrair número do processo
                numero_processo = processo_tag.get('numero', '')
                if not numero_processo:
                    continue
                
                # Extrair NOME DA MARCA (tag <nome> dentro de <marca>)
                # Se não existir no XML, será extraído do PDF
                marca = None
                marca_tag = processo_tag.find('marca')
                
                if marca_tag:
                    nome_marca_tag = marca_tag.find('nome')
                    if nome_marca_tag:
                        marca = nome_marca_tag.get_text(strip=True)
                
                # Email será extraído do PDF pelo pePI scraper
                email = None
                
                # Verificar se tem procurador
                tem_procurador = False
                procurador_tag = processo_tag.find('procurador')
                if procurador_tag and procurador_tag.get_text(strip=True):
                    tem_procurador = True
                
                processo_dict = {
                    'id': str(uuid.uuid4()),
                    'execucao_id': execucao_id,
                    'numero_processo': numero_processo,
                    'marca': marca or 'Não informado',
                    'email': email,
                    'tem_procurador': tem_procurador,
                    'data_extracao': datetime.now(timezone.utc).isoformat(),
                    'semana': semana,
                    'ano': ano
                }
                
                processos.append(processo_dict)
                
            except Exception as e:
                logger.error(f"Erro ao processar despacho: {str(e)}")
                continue
        
        logger.info(f"Total de {len(processos)} processos extraídos com sucesso")
        return processos
        
    except Exception as e:
        logger.error(f"Erro ao parsear XML: {str(e)}")
        return []