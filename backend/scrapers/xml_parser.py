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
                
                # Extrair marca do titular (atributo nome-razao-social)
                marca = 'Não informado'
                titular_tag = processo_tag.find('titular')
                if titular_tag:
                    marca = titular_tag.get('nome-razao-social', 'Não informado')
                
                # Extrair email (pode estar como atributo ou tag)
                email = None
                if titular_tag:
                    # Tentar pegar email como atributo
                    email = titular_tag.get('email')
                    
                    # Se não encontrou, tentar como tag
                    if not email:
                        email_tag = titular_tag.find('email')
                        if email_tag:
                            email = email_tag.get_text(strip=True)
                
                processo_dict = {
                    'id': str(uuid.uuid4()),
                    'execucao_id': execucao_id,
                    'numero_processo': numero_processo,
                    'marca': marca or 'Não informado',
                    'email': email,
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