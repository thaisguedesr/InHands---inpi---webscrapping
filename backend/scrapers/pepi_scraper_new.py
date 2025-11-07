import logging
from playwright.sync_api import sync_playwright
import time
import re
from PyPDF2 import PdfReader
import io
import os
from capmonster_python import CapmonsterClient, RecaptchaV2Task

logger = logging.getLogger(__name__)

class PepiScraper:
    def __init__(self):
        self.login_user = "InHandsC"
        self.login_pass = "Marcas01"
        self.base_url = "https://busca.inpi.gov.br/pePI/"
        self.capmonster_api_key = os.environ.get('CAPMONSTER_API_KEY', 'feeda35a6d124c535a42e3b2ff997bc6')
    
    def extrair_dados_de_pdf(self, pdf_content: bytes) -> dict:
        """Extrai marca (Elemento Nominativo) e email do PDF"""
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_content))
            texto_completo = ""
            
            # Extrair texto de todas as páginas
            for page in pdf_reader.pages:
                texto_completo += page.extract_text()
            
            resultado = {
                'marca': None,
                'email': None
            }
            
            # Extrair MARCA (Elemento Nominativo)
            # Padrão: "Elemento Nominativo: NOME DA MARCA"
            marca_pattern = r'Elemento Nominativo:\s*(.+?)(?:\n|$)'
            marca_match = re.search(marca_pattern, texto_completo, re.IGNORECASE)
            if marca_match:
                resultado['marca'] = marca_match.group(1).strip()
                logger.info(f"Marca encontrada no PDF: {resultado['marca']}")
            else:
                logger.warning("Marca (Elemento Nominativo) não encontrada no PDF")
            
            # Extrair EMAIL
            # Regex para encontrar emails
            email_pattern = r'e-mail:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
            email_match = re.search(email_pattern, texto_completo, re.IGNORECASE)
            
            if email_match:
                resultado['email'] = email_match.group(1).strip()
                logger.info(f"Email encontrado no PDF: {resultado['email']}")
            else:
                # Tentar regex genérico se não encontrar com "e-mail:"
                email_generic = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_generic, texto_completo)
                if emails:
                    resultado['email'] = emails[0]
                    logger.info(f"Email encontrado no PDF (genérico): {resultado['email']}")
                else:
                    logger.warning("Nenhum email encontrado no PDF")
            
            return resultado
                
        except Exception as e:
            logger.error(f"Erro ao extrair dados do PDF: {str(e)}")
            return {'marca': None, 'email': None}
    
    def resolver_recaptcha(self, page_url: str, site_key: str) -> str:
        """
        Resolve o reCAPTCHA usando CapMonster API
        Retorna o token g-recaptcha-response
        """
        try:
            logger.info(f"Resolvendo reCAPTCHA com site_key: {site_key}")
            
            # Criar cliente CapMonster
            capmonster = CapmonsterClient(self.capmonster_api_key)
            
            # Criar task de reCAPTCHA v2
            task = RecaptchaV2Task(
                websiteURL=page_url,
                websiteKey=site_key
            )
            
            # Criar a task no CapMonster
            task_id = capmonster.create_task(task)
            logger.info(f"Task criada no CapMonster com ID: {task_id}")
            
            # Aguardar e obter o resultado
            result = capmonster.join_task_result(task_id)
            logger.info(f"Resultado do CapMonster: {result}")
            
            # Extrair o token
            token = result.get('gRecaptchaResponse')
            if not token:
                # Tentar alternativa
                token = result.get('solution', {}).get('gRecaptchaResponse')
            
            if token:
                logger.info("reCAPTCHA resolvido com sucesso!")
                return token
            else:
                raise Exception(f"Token não encontrado no resultado: {result}")
            
        except Exception as e:
            logger.error(f"Erro ao resolver reCAPTCHA: {str(e)}")
            raise

    def buscar_processo_e_extrair_dados(self, numero_processo: str) -> dict:
        """
        Faz login no pePI, busca o processo, resolve CAPTCHA e extrai marca e email do PDF
        Retorna: {'marca': str, 'email': str}
        """
        try:
            with sync_playwright() as p:
                # Iniciar browser
                browser = p.chromium.launch(
                    headless=True,
                    executable_path='/pw-browsers/chromium_headless_shell-1187/chrome-linux/headless_shell',
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
                context = browser.new_context()
                page = context.new_page()
                
                logger.info(f"Acessando pePI para processo {numero_processo}")
                
                # 1. Acessar página de login
                page.goto(self.base_url, timeout=30000)
                page.wait_for_load_state("networkidle")
                
                # 2. Fazer login
                page.fill('input[name="T_Login"]', self.login_user)
                page.fill('input[name="T_Senha"]', self.login_pass)
                page.click('input[type="submit"]')
                page.wait_for_load_state("networkidle", timeout=60000)
                time.sleep(2)
                logger.info("Login realizado")
                
                # 3. Ir para Pesquisa de Marcas por número de processo
                page.goto("https://busca.inpi.gov.br/pePI/jsp/marcas/Pesquisa_num_processo.jsp", timeout=60000)
                page.wait_for_load_state("networkidle")
                time.sleep(1)
                logger.info("Página de pesquisa carregada")
                
                # 4. Preencher número do processo e pesquisar
                page.fill('input[name="NumPedido"]', numero_processo)
                page.click('input[type="submit"][name="botao"]')
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                logger.info(f"Pesquisa realizada para processo {numero_processo}")
                
                # 5. Clicar no link dos detalhes do processo
                detail_link = page.locator('a[href*="Action=detail"]').first
                if detail_link.count() == 0:
                    logger.warning(f"Processo {numero_processo} não encontrado nos resultados")
                    browser.close()
                    return {'marca': None, 'email': None}
                
                detail_link.click()
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                logger.info("Página de detalhes carregada")
                
                # 6. Clicar no link de petições
                peticoes_link = page.locator('a:has-text("Clique aqui para ter acesso")').first
                if peticoes_link.count() == 0:
                    logger.warning("Link de petições não encontrado")
                    browser.close()
                    return {'marca': None, 'email': None}
                
                peticoes_link.click()
                time.sleep(3)
                logger.info("Link de petições clicado")
                
                # 7. Procurar ícone do PDF (código 300 - primeiro PDF da lista)
                # O PDF que queremos é o primeiro da petição (código 300)
                pdf_icon = page.locator('img[name="certificadoPublicacao"]').first
                
                if pdf_icon.count() == 0:
                    logger.warning("Ícone do PDF não encontrado")
                    browser.close()
                    return {'marca': None, 'email': None}
                
                logger.info("Ícone do PDF encontrado")
                
                # 8. Clicar no ícone do PDF (isso abrirá o modal do CAPTCHA)
                pdf_icon.click()
                time.sleep(2)
                logger.info("Clicou no ícone do PDF - modal do CAPTCHA deve ter aparecido")
                
                # 9. Resolver o reCAPTCHA
                # Site key é sempre o mesmo: 6LfhwSAaAAAAANyx2xt8Ikk-YkQ3PGeAVhCfF3i2
                site_key = "6LfhwSAaAAAAANyx2xt8Ikk-YkQ3PGeAVhCfF3i2"
                current_url = page.url
                
                logger.info(f"Resolvendo reCAPTCHA com site_key: {site_key}")
                captcha_token = self.resolver_recaptcha(current_url, site_key)
                
                # 10. Injetar o token na página
                page.evaluate(f"""
                    () => {{
                        const responseField = document.querySelector('[name="g-recaptcha-response"]');
                        if (responseField) {{
                            responseField.value = "{captcha_token}";
                            responseField.innerHTML = "{captcha_token}";
                        }}
                        // Também tentar via textarea id
                        const textarea = document.getElementById('g-recaptcha-response');
                        if (textarea) {{
                            textarea.value = "{captcha_token}";
                            textarea.innerHTML = "{captcha_token}";
                        }}
                    }}
                """)
                
                logger.info("Token do CAPTCHA injetado!")
                time.sleep(1)
                
                # 11. Clicar no botão de download
                download_btn = page.locator('#captchaButton')
                if download_btn.count() > 0:
                    logger.info("Clicando no botão de download...")
                    
                    # Aguardar o download
                    with page.expect_download(timeout=30000) as download_info:
                        download_btn.click()
                    
                    download = download_info.value
                    logger.info(f"Download iniciado: {download.suggested_filename}")
                    
                    # Ler o conteúdo do PDF
                    pdf_path = download.path()
                    with open(pdf_path, 'rb') as f:
                        pdf_content = f.read()
                    
                    logger.info("PDF baixado com sucesso!")
                    
                    # 12. Extrair marca e email do PDF
                    dados = self.extrair_dados_de_pdf(pdf_content)
                    
                    browser.close()
                    return dados
                else:
                    logger.error("Botão de download não encontrado após resolver CAPTCHA")
                    browser.close()
                    return {'marca': None, 'email': None}
                    
        except Exception as e:
            logger.error(f"Erro ao buscar processo {numero_processo} no pePI: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'marca': None, 'email': None}
