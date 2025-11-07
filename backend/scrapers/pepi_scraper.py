import logging
from playwright.sync_api import sync_playwright
import time
import re
from PyPDF2 import PdfReader
import io
import os

logger = logging.getLogger(__name__)

class PepiScraper:
    def __init__(self):
        self.login_user = "InHandsC"
        self.login_pass = "Marcas01"
        self.base_url = "https://busca.inpi.gov.br/pePI/"
    
    def extrair_email_de_pdf(self, pdf_content: bytes) -> str:
        """Extrai email de um PDF"""
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_content))
            texto_completo = ""
            
            # Extrair texto de todas as páginas
            for page in pdf_reader.pages:
                texto_completo += page.extract_text()
            
            # Regex para encontrar emails
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, texto_completo)
            
            if emails:
                # Retornar primeiro email encontrado
                logger.info(f"Email encontrado no PDF: {emails[0]}")
                return emails[0]
            else:
                logger.warning("Nenhum email encontrado no PDF")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao extrair email do PDF: {str(e)}")
            return None
    
    def buscar_processo_e_extrair_email(self, numero_processo: str) -> str:
        """
        Faz login no pePI, busca o processo e extrai o email do PDF código 300
        """
        try:
            with sync_playwright() as p:
                # Iniciar browser
                browser = p.chromium.launch(
                    headless=True,
                    executable_path='/pw-browsers/chromium-1187/chrome-linux/chrome',
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
                context = browser.new_context()
                page = context.new_page()
                
                logger.info(f"Acessando pePI para processo {numero_processo}")
                
                # 1. Acessar página de login
                page.goto(self.base_url, timeout=30000)
                page.wait_for_load_state("networkidle")
                
                # 2. Fazer login
                page.fill('input[name="login"]', self.login_user)
                page.fill('input[name="senha"]', self.login_pass)
                page.click('button:has-text("Continuar")')
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                
                # 3. Clicar em "Marcas"
                page.click('text=Marca')
                page.wait_for_load_state("networkidle")
                time.sleep(1)
                
                # 4. Ir para Pesquisa Básica
                page.click('text=Pesquisa Básica')
                page.wait_for_load_state("networkidle")
                time.sleep(1)
                
                # 5. Preencher número do processo
                page.fill('input[name="processo"]', numero_processo)
                page.click('button:has-text("pesquisar")')
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                
                # 6. Buscar link do PDF código 300
                # O código 300 geralmente está em um link específico
                # Tentar encontrar link com código 300
                pdf_link = None
                
                # Tentar diferentes seletores
                links = page.query_selector_all('a[href*="300"]')
                if not links:
                    links = page.query_selector_all('a[href*="pdf"]')
                
                if links:
                    pdf_link = links[0].get_attribute('href')
                    
                    if not pdf_link.startswith('http'):
                        pdf_link = f"{self.base_url.rstrip('/')}/{pdf_link.lstrip('/')}"
                    
                    logger.info(f"Link PDF encontrado: {pdf_link}")
                    
                    # 7. Baixar PDF
                    pdf_response = page.request.get(pdf_link)
                    pdf_content = pdf_response.body()
                    
                    # 8. Extrair email do PDF
                    email = self.extrair_email_de_pdf(pdf_content)
                    
                    browser.close()
                    return email
                else:
                    logger.warning(f"PDF código 300 não encontrado para processo {numero_processo}")
                    browser.close()
                    return None
                    
        except Exception as e:
            logger.error(f"Erro ao buscar processo {numero_processo} no pePI: {str(e)}")
            return None
