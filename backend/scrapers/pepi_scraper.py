import logging
from playwright.sync_api import sync_playwright
import time
import re
from PyPDF2 import PdfReader
import io
import os
from capmonster_python import CapMonsterClient, RecaptchaV2Task

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
            
            capmonster = CapMonsterClient(self.capmonster_api_key)
            task = RecaptchaV2Task(
                website_url=page_url,
                website_key=site_key
            )
            
            # Resolver o captcha (pode levar alguns segundos)
            result = capmonster.solve_captcha(task)
            token = result.get('gRecaptchaResponse')
            
            logger.info("reCAPTCHA resolvido com sucesso!")
            return token
            
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
                page.fill('input[name="T_Login"]', self.login_user)
                page.fill('input[name="T_Senha"]', self.login_pass)
                page.click('input[type="submit"]')
                page.wait_for_load_state("networkidle", timeout=60000)
                time.sleep(3)
                
                # 3. Ir direto para Pesquisa de Marcas por número de processo
                page.goto("https://busca.inpi.gov.br/pePI/jsp/marcas/Pesquisa_num_processo.jsp", timeout=60000)
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                
                # 4. Preencher número do processo e pesquisar
                page.fill('input[name="processo"]', numero_processo)
                page.click('button:has-text("pesquisar")')
                page.wait_for_load_state("networkidle")
                time.sleep(3)
                
                # 5. Clicar em "Clique aqui para ter acesso as petições do processo"
                try:
                    peticoes_link = page.locator('a:has-text("Clique aqui para ter acesso as petições do processo")')
                    if peticoes_link.count() > 0:
                        peticoes_link.click()
                        logger.info("Clicou no link de petições")
                        time.sleep(2)
                    else:
                        logger.warning("Link de petições não encontrado")
                except Exception as e:
                    logger.warning(f"Erro ao clicar no link de petições: {str(e)}")
                
                # 6. Lidar com popup de "finalidade de acesso"
                try:
                    # Aguardar o popup aparecer (pode ser em uma nova janela/popup)
                    time.sleep(2)
                    
                    # Verificar se há um popup ou nova página
                    if len(context.pages) > 1:
                        popup_page = context.pages[-1]
                        logger.info("Popup detectado, preenchendo finalidade de acesso")
                        
                        # Selecionar uma opção no dropdown de finalidade
                        finalidade_select = popup_page.locator('select[name="finalidade"]')
                        if finalidade_select.count() > 0:
                            popup_page.select_option('select[name="finalidade"]', index=1)
                            logger.info("Finalidade selecionada")
                        
                        # Marcar checkbox de concordância
                        checkbox = popup_page.locator('input[type="checkbox"]')
                        if checkbox.count() > 0:
                            checkbox.check()
                            logger.info("Checkbox marcado")
                        
                        # Clicar em "Enviar"
                        enviar_btn = popup_page.locator('input[type="submit"], button:has-text("Enviar")')
                        if enviar_btn.count() > 0:
                            enviar_btn.click()
                            logger.info("Clicou em Enviar no popup")
                            time.sleep(2)
                        
                        # Voltar para a página principal
                        page = context.pages[0]
                    else:
                        # Popup pode estar na mesma página (modal)
                        finalidade_select = page.locator('select[name="finalidade"]')
                        if finalidade_select.count() > 0:
                            page.select_option('select[name="finalidade"]', index=1)
                            page.locator('input[type="checkbox"]').first.check()
                            page.locator('input[type="submit"], button:has-text("Enviar")').first.click()
                            logger.info("Modal de finalidade preenchido na página principal")
                            time.sleep(2)
                            
                except Exception as e:
                    logger.warning(f"Erro ao lidar com popup de finalidade: {str(e)}")
                
                # 7. Procurar ícone do PDF (códigos 389 ou 394, NÃO 300)
                # Remover overlays que possam estar bloqueando
                page.evaluate("""
                    () => {
                        const overlays = document.querySelectorAll('.overlay, .modal-backdrop, #overlay');
                        overlays.forEach(el => el.remove());
                    }
                """)
                
                time.sleep(1)
                
                # Procurar por imagens/links de PDF com códigos 389 ou 394
                pdf_icon = None
                for codigo in ['389', '394']:
                    # Tentar encontrar imagem com onclick que contenha o código
                    icons = page.query_selector_all(f'img[onclick*="{codigo}"]')
                    if icons:
                        pdf_icon = icons[0]
                        logger.info(f"Ícone PDF encontrado com código {codigo}")
                        break
                
                if not pdf_icon:
                    # Tentar encontrar qualquer ícone de PDF
                    icons = page.query_selector_all('img[onclick*="pdf"], img[src*="pdf"]')
                    if icons:
                        pdf_icon = icons[0]
                        logger.info("Ícone PDF encontrado (genérico)")
                
                if pdf_icon:
                    # 8. Clicar no ícone do PDF (isso abrirá o modal do CAPTCHA)
                    logger.info("Clicando no ícone do PDF...")
                    pdf_icon.click(force=True)
                    time.sleep(3)
                    
                    # 9. Detectar e resolver o reCAPTCHA
                    try:
                        # Procurar pelo site_key do reCAPTCHA
                        site_key = page.evaluate("""
                            () => {
                                const recaptchaElement = document.querySelector('.g-recaptcha');
                                if (recaptchaElement) {
                                    return recaptchaElement.getAttribute('data-sitekey');
                                }
                                
                                // Procurar no código fonte
                                const scripts = document.querySelectorAll('script');
                                for (let script of scripts) {
                                    const match = script.textContent.match(/data-sitekey=["']([^"']+)["']/);
                                    if (match) return match[1];
                                    
                                    const match2 = script.textContent.match(/sitekey:\s*["']([^"']+)["']/);
                                    if (match2) return match2[1];
                                }
                                return null;
                            }
                        """)
                        
                        if site_key:
                            logger.info(f"Site key encontrado: {site_key}")
                            
                            # Resolver o CAPTCHA com CapMonster
                            current_url = page.url
                            captcha_token = self.resolver_recaptcha(current_url, site_key)
                            
                            # Injetar o token na página
                            page.evaluate(f"""
                                () => {{
                                    const responseField = document.querySelector('[name="g-recaptcha-response"]');
                                    if (responseField) {{
                                        responseField.value = "{captcha_token}";
                                        responseField.innerHTML = "{captcha_token}";
                                    }}
                                }}
                            """)
                            
                            logger.info("Token do CAPTCHA injetado!")
                            time.sleep(1)
                            
                            # Clicar no botão de download que estava escondido
                            download_btn = page.locator('#captchaButton, input[type="submit"][value="Download"]')
                            if download_btn.count() > 0:
                                # Aguardar o download
                                with page.expect_download() as download_info:
                                    download_btn.click()
                                    download = download_info.value
                                    
                                # Ler o conteúdo do PDF
                                pdf_content = download.path().read_bytes()
                                logger.info("PDF baixado com sucesso!")
                                
                                # Extrair marca e email do PDF
                                dados = self.extrair_dados_de_pdf(pdf_content)
                                browser.close()
                                return dados
                            else:
                                logger.warning("Botão de download não encontrado após resolver CAPTCHA")
                        else:
                            logger.warning("Site key do reCAPTCHA não encontrado")
                            
                    except Exception as e:
                        logger.error(f"Erro ao resolver CAPTCHA e baixar PDF: {str(e)}")
                
                else:
                    logger.warning(f"Ícone do PDF não encontrado para processo {numero_processo}")
                
                browser.close()
                return {'marca': None, 'email': None}
                    
        except Exception as e:
            logger.error(f"Erro ao buscar processo {numero_processo} no pePI: {str(e)}")
            return {'marca': None, 'email': None}
