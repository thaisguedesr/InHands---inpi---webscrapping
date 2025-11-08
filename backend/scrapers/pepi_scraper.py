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
            
            # ============ EXTRAIR MARCA (Elemento Nominativo em Dados da Marca) ============
            # A marca aparece ANTES de "Elemento Nominativo:", não depois!
            # Formato: "Natureza:\n[NOME DA MARCA] Elemento Nominativo:"
            
            # Procurar por texto que vem ANTES de "Elemento Nominativo:"
            marca_pattern = r'Natureza:\s*\n?\s*([^\n]+?)\s+Elemento\s+Nominativo'
            marca_match = re.search(marca_pattern, texto_completo, re.IGNORECASE | re.DOTALL)
            
            if marca_match:
                marca_text = marca_match.group(1).strip()
                # Limpar possíveis caracteres extras
                marca_text = ' '.join(marca_text.split())
                
                if len(marca_text) > 1 and not marca_text.lower() in ('mista', 'nominativa', 'figurativa', 'tridimensional'):
                    resultado['marca'] = marca_text
                    logger.info(f"Marca encontrada no PDF: {resultado['marca']}")
            
            # Se não encontrou, tentar padrão alternativo
            if not resultado['marca']:
                # Às vezes o nome vem depois
                marca_pattern2 = r'Elemento\s+Nominativo[:\s]+([^\n]+)'
                marca_match2 = re.search(marca_pattern2, texto_completo, re.IGNORECASE)
                
                if marca_match2:
                    marca_text = marca_match2.group(1).strip()
                    marca_text = marca_text.split('\n')[0].strip()
                    marca_text = ' '.join(marca_text.split())
                    
                    # Validar que não é texto genérico
                    palavras_invalidas = ['marca possui', 'não se aplica', 'sim', 'não', 'mista', 'nominativa']
                    if len(marca_text) > 1 and not any(inv in marca_text.lower() for inv in palavras_invalidas):
                        resultado['marca'] = marca_text
                        logger.info(f"Marca encontrada no PDF (padrão 2): {resultado['marca']}")
            
            if not resultado['marca']:
                logger.warning("Marca (Elemento Nominativo) não encontrada no PDF")
            
            # ============ EXTRAIR EMAIL (Dados Gerais ou Dados do Requerente) ============
            # Procurar nas seções específicas primeiro
            
            # 1. Procurar na seção "Dados Gerais"
            dados_gerais_match = re.search(r'Dados\s+Gerais(.*?)(?:Dados\s+da\s+Marca|Dados\s+do\s+Procurador|$)', 
                                          texto_completo, re.IGNORECASE | re.DOTALL)
            
            if dados_gerais_match:
                secao_dados_gerais = dados_gerais_match.group(1)
                email_match = re.search(r'e-?mail[:\s]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', 
                                       secao_dados_gerais, re.IGNORECASE)
                if email_match:
                    resultado['email'] = email_match.group(1).strip().lower()
                    logger.info(f"Email encontrado em Dados Gerais: {resultado['email']}")
            
            # 2. Se não encontrou, procurar na seção "Dados do(s) requerente(s)"
            if not resultado['email']:
                requerente_match = re.search(r'Dados\s+do\(?s?\)?\s+requerente\(?s?\)?(.*?)(?:Dados\s+da\s+Marca|Dados\s+do\s+Procurador|$)', 
                                            texto_completo, re.IGNORECASE | re.DOTALL)
                
                if requerente_match:
                    secao_requerente = requerente_match.group(1)
                    email_match = re.search(r'e-?mail[:\s]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', 
                                          secao_requerente, re.IGNORECASE)
                    if email_match:
                        resultado['email'] = email_match.group(1).strip().lower()
                        logger.info(f"Email encontrado em Dados do Requerente: {resultado['email']}")
            
            # 3. Fallback: procurar qualquer email no documento
            if not resultado['email']:
                email_match = re.search(r'e-?mail[:\s]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', 
                                       texto_completo, re.IGNORECASE)
                if email_match:
                    resultado['email'] = email_match.group(1).strip().lower()
                    logger.info(f"Email encontrado no PDF (genérico): {resultado['email']}")
            
            if not resultado['email']:
                logger.warning("Nenhum email encontrado no PDF")
            
            return resultado
                
        except Exception as e:
            logger.error(f"Erro ao extrair dados do PDF: {str(e)}")
            return {'marca': None, 'email': None}
    
    def _descadastrar_processo(self, page, numero_processo):
        """Descadastra o processo clicando em Listagem de Terceiros Interessados Habilitados"""
        try:
            # Procurar o link "Listagem de Terceiros Interessados Habilitados"
            link_descadastrar = page.locator('a:has-text("Listagem de Terceiros Interessados Habilitados")').first
            
            if link_descadastrar.count() == 0:
                logger.warning("  ⚠️  Link de descadastramento não encontrado")
                return
            
            logger.info("  🔗 Link de descadastramento encontrado - clicando...")
            
            # O link abre um popup
            with page.expect_popup(timeout=5000) as popup_info:
                link_descadastrar.click()
            
            popup_page = popup_info.value
            popup_page.wait_for_load_state("networkidle", timeout=10000)
            logger.info("  📋 Popup de terceiros aberto")
            
            # Procurar botão/link de descadastrar ou desabilitar
            # Pode ser um botão "Descadastrar", "Desabilitar", ou checkbox
            botao_descadastrar = None
            
            # Tentar diferentes seletores
            seletores_descadastrar = [
                'button:has-text("Descadastrar")',
                'input[value*="Descadastrar"]',
                'a:has-text("Descadastrar")',
                'button:has-text("Desabilitar")',
                'a:has-text("Desabilitar")'
            ]
            
            for seletor in seletores_descadastrar:
                botao = page.locator(seletor)
                if botao.count() > 0:
                    botao_descadastrar = botao.first
                    logger.info(f"  ✅ Botão de descadastramento encontrado: {seletor}")
                    break
            
            if botao_descadastrar:
                botao_descadastrar.click()
                time.sleep(1)
                logger.info(f"  ✅ Processo {numero_processo} descadastrado com sucesso!")
            else:
                logger.warning("  ⚠️  Botão de descadastramento não encontrado na página")
                # Salvar HTML para debug
                with open(f"/tmp/descadastrar_{numero_processo}.html", "w") as f:
                    f.write(page.content())
                logger.info(f"  📄 HTML salvo em: /tmp/descadastrar_{numero_processo}.html")
                
        except Exception as e:
            logger.warning(f"  ⚠️  Erro ao descadastrar processo: {str(e)}")
    
    def _procurar_pdf_389_394(self, page):
        """Procura PDF com Serviço 389 ou 394 na tabela"""
        try:
            all_rows = page.locator('table tr').all()
            logger.info(f"  📊 Total de linhas na tabela: {len(all_rows)}")
            
            for row in all_rows:
                try:
                    cells = row.locator('td').all()
                    row_text = " ".join([c.inner_text().strip() for c in cells])
                    
                    if '389' in row_text or '394' in row_text:
                        codigo_encontrado = '389' if '389' in row_text else '394'
                        logger.info(f"  🔍 Linha com código {codigo_encontrado} encontrada")
                        
                        pdf_in_row = row.locator('img[src*="pdf.gif"]')
                        
                        if pdf_in_row.count() > 0:
                            logger.info(f"  ✅ Encontrado ícone PDF na linha com Serviço {codigo_encontrado}!")
                            return pdf_in_row.first
                        else:
                            logger.warning(f"  ⚠️  Linha tem {codigo_encontrado} mas não encontrou ícone PDF")
                except:
                    continue
            
            return None
        except Exception as e:
            logger.error(f"  ❌ Erro ao procurar PDF: {str(e)}")
            return None
    
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
                # Iniciar browser com contexto NOVO (sem cookies) para garantir que o link apareça
                browser = p.chromium.launch(
                    headless=True,
                    executable_path='/pw-browsers/chromium_headless_shell-1187/chrome-linux/headless_shell',
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
                # Criar contexto completamente novo (sem cache/cookies)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True
                )
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
                
                # 5.1 EXTRAIR A MARCA diretamente da página de detalhes
                marca_extraida = None
                try:
                    # Procurar pela seção "Marca:" na página
                    # Formato: <td>Marca:</td> seguido de <td> com o nome
                    marca_cell = page.locator('td:has-text("Marca:")').first
                    if marca_cell.count() > 0:
                        # Pegar a próxima célula (que contém o nome da marca)
                        parent_row = marca_cell.locator('xpath=..').first  # Pegar o <tr>
                        cells = parent_row.locator('td').all()
                        
                        if len(cells) >= 2:
                            marca_text = cells[1].inner_text()
                            marca_extraida = marca_text.strip()
                            logger.info(f"✅ MARCA extraída da página: {marca_extraida}")
                except Exception as e:
                    logger.warning(f"⚠️  Erro ao extrair marca da página: {str(e)}")
                
                # 5.2 Verificar se é marca figurativa (se for, pular)
                page_content = page.content()
                if 'Figurativa' in page_content:
                    logger.warning(f"⚠️  Processo {numero_processo} é FIGURATIVA - pulando")
                    browser.close()
                    return {'marca': None, 'email': None, 'tipo': 'figurativa'}
                
                logger.info("✅ Marca não é figurativa, continuando...")
                
                # 6. EXPANDIR a seção de Petições (accordion)
                # O conteúdo está colapsado por padrão!
                logger.info("📂 Expandindo seção Petições...")
                try:
                    # Verificar se já está expandido
                    accordion_checkbox = page.locator('#accordion-1')
                    is_checked = accordion_checkbox.is_checked()
                    
                    if not is_checked:
                        # Clicar no accordion para abrir
                        accordion_peticoes = page.locator('label[for="accordion-1"]')
                        if accordion_peticoes.count() > 0:
                            accordion_peticoes.click()
                            logger.info("  ✅ Accordion clicado")
                    else:
                        logger.info("  ℹ️  Accordion já estava expandido")
                    
                    # Aguardar o conteúdo carregar (importante!)
                    time.sleep(3)
                    page.wait_for_load_state("networkidle", timeout=10000)
                    logger.info("  ✅ Conteúdo carregado")
                    
                except Exception as e:
                    logger.warning(f"  ⚠️  Erro ao expandir: {str(e)}")
                    time.sleep(2)
                
                # 6.1 PRIMEIRO: Procurar PDF com Serviço 389/394
                time.sleep(1)
                logger.info("🔍 1ª TENTATIVA: Procurando PDF com Serviço 389 ou 394...")
                
                pdf_icon_tentativa1 = self._procurar_pdf_389_394(page)
                
                if pdf_icon_tentativa1:
                    logger.info("✅ PDF 389/394 encontrado na 1ª tentativa!")
                    pdf_icon = pdf_icon_tentativa1
                    pdf_escolhido = "389 ou 394"
                else:
                    # NÃO encontrou - precisa clicar no "Clique aqui..."
                    logger.info("📋 PDF 389/394 NÃO encontrado - procurando link 'Clique aqui...'")
                    
                    peticoes_link = page.locator('a:has-text("Clique aqui para ter acesso")').first
                    
                    if peticoes_link.count() == 0:
                        logger.error("❌ Link 'Clique aqui...' também não encontrado!")
                        browser.close()
                        return {'marca': marca_extraida, 'email': None}
                    
                    logger.info("📋 Link 'Clique aqui...' encontrado - clicando...")
                    
                    # O link abre em uma NOVA JANELA/TAB (popup)
                    # Aguardar nova janela aparecer
                    logger.info("  🖱️  2º AÇÃO: Clicando no link...")
                    try:
                        with page.expect_popup(timeout=5000) as popup_info:
                            peticoes_link.click()
                            logger.info("  ✅ Link clicado - aguardando popup...")
                        
                        popup_page = popup_info.value
                        popup_page.wait_for_load_state("networkidle", timeout=10000)
                        logger.info("📋 Popup de finalidade aberto")
                        
                        # Preencher o formulário no popup
                        try:
                            # Selecionar finalidade específica
                            selects = popup_page.locator('select')
                            if selects.count() > 0:
                                # Tentar selecionar por texto primeiro
                                try:
                                    selects.first.select_option(label="Pesquisa para Fins Profissionais ou Acadêmicos")
                                    logger.info("  ✅ Finalidade selecionada: 'Pesquisa para Fins Profissionais ou Acadêmicos'")
                                except:
                                    # Fallback para index 1 se não encontrar por texto
                                    selects.first.select_option(index=1)
                                    logger.info("  ✅ Finalidade selecionada (index 1)")
                            
                            # Marcar o checkbox
                            checkboxes = popup_page.locator('input[type="checkbox"]')
                            if checkboxes.count() > 0:
                                checkboxes.first.check()
                                logger.info("  ✅ Checkbox marcado")
                            
                            # Clicar no botão Enviar
                            enviar_btn = popup_page.locator('button:has-text("Enviar"), input[value="Enviar"]')
                            if enviar_btn.count() > 0:
                                enviar_btn.first.click()
                                logger.info("  ✅ Formulário enviado")
                                
                                # Aguardar página principal recarregar
                                time.sleep(3)
                                page.wait_for_load_state("networkidle", timeout=15000)
                                logger.info("  📄 Página recarregada - PDFs devem estar visíveis agora")
                        
                        except Exception as e:
                            logger.warning(f"  ⚠️  Erro no popup: {str(e)}")
                            time.sleep(2)
                    
                    except Exception as e:
                        logger.warning(f"⚠️  Erro ao abrir popup: {str(e)}")
                        time.sleep(2)
                    
                    # Agora procurar o PDF novamente
                    logger.info("🔍 2ª TENTATIVA: Procurando PDF com Serviço 389 ou 394 após clicar no link...")
                    time.sleep(2)
                    
                    pdf_icon_tentativa2 = self._procurar_pdf_389_394(page)
                    
                    if pdf_icon_tentativa2:
                        logger.info("✅ PDF 389/394 encontrado na 2ª tentativa!")
                        pdf_icon = pdf_icon_tentativa2
                        pdf_escolhido = "389 ou 394"
                    else:
                        logger.error("❌ PDF 389/394 NÃO encontrado mesmo após clicar no link!")
                        browser.close()
                        return {'marca': marca_extraida, 'email': None}
                
                # 7. Clicar no ícone do PDF encontrado
                logger.info(f"🖱️  Clicando no PDF escolhido: {pdf_escolhido}")
                pdf_icon.click()
                time.sleep(2)
                logger.info("  ✅ Clicou no ícone do PDF - modal do CAPTCHA deve ter aparecido")
                
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
                download_btn = page.locator('#captchaButton').first
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
                    
                    # Salvar uma cópia para debug (opcional)
                    debug_path = f"/tmp/debug_{numero_processo}.pdf"
                    with open(debug_path, 'wb') as f:
                        f.write(pdf_content)
                    logger.info(f"PDF salvo em: {debug_path}")
                    
                    logger.info("PDF baixado com sucesso!")
                    
                    # 12. Extrair EMAIL do PDF (MARCA já foi extraída da página)
                    dados = self.extrair_dados_de_pdf(pdf_content)
                    
                    # Usar a marca extraída da página em vez do PDF
                    if marca_extraida:
                        dados['marca'] = marca_extraida
                        logger.info(f"✅ Usando MARCA da página: {marca_extraida}")
                    
                    # 13. DESCADASTRAR processo antes de passar ao próximo
                    if dados.get('email'):
                        logger.info("📋 Descadastrando processo...")
                        self._descadastrar_processo(page, numero_processo)
                    
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
