#!/usr/bin/env python3
"""
Script de DEBUG para o PepiScraper - com screenshots
"""
import sys
sys.path.append('/app/backend')

from playwright.sync_api import sync_playwright
import time
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def debug_pepi_navigation():
    """Debug detalhado da navegação no pePI"""
    
    login_user = "InHandsC"
    login_pass = "Marcas01"
    base_url = "https://busca.inpi.gov.br/pePI/"
    numero_processo = "907206638"  # Fornecido pelo usuário
    
    with sync_playwright() as p:
        # Iniciar browser em modo não-headless para debug
        browser = p.chromium.launch(
            headless=False,
            executable_path='/pw-browsers/chromium_headless_shell-1187/chrome-linux/headless_shell',
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # 1. Acessar página de login
            logger.info("1. Acessando página de login...")
            page.goto(base_url, timeout=30000)
            page.wait_for_load_state("networkidle")
            page.screenshot(path="/app/step1_login_page.png")
            logger.info("   ✅ Screenshot salvo: step1_login_page.png")
            
            # Verificar campos de login
            login_field = page.locator('input[name="T_Login"]')
            pass_field = page.locator('input[name="T_Senha"]')
            logger.info(f"   Campo login encontrado: {login_field.count() > 0}")
            logger.info(f"   Campo senha encontrado: {pass_field.count() > 0}")
            
            # 2. Fazer login
            logger.info("2. Preenchendo credenciais...")
            page.fill('input[name="T_Login"]', login_user)
            page.fill('input[name="T_Senha"]', login_pass)
            page.screenshot(path="/app/step2_credentials_filled.png")
            logger.info("   ✅ Screenshot salvo: step2_credentials_filled.png")
            
            logger.info("3. Clicando em submit...")
            page.click('input[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=60000)
            time.sleep(3)
            page.screenshot(path="/app/step3_after_login.png")
            logger.info("   ✅ Screenshot salvo: step3_after_login.png")
            logger.info(f"   URL atual: {page.url}")
            
            # 3. Ir para pesquisa de marcas
            logger.info("4. Navegando para pesquisa de marcas...")
            page.goto("https://busca.inpi.gov.br/pePI/jsp/marcas/Pesquisa_num_processo.jsp", timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            page.screenshot(path="/app/step4_search_page.png")
            logger.info("   ✅ Screenshot salvo: step4_search_page.png")
            logger.info(f"   URL atual: {page.url}")
            
            # Verificar campo de processo
            processo_field = page.locator('input[name="NumPedido"]')
            logger.info(f"   Campo processo (NumPedido) encontrado: {processo_field.count() > 0}")
            
            if processo_field.count() == 0:
                # Tentar outros seletores
                logger.info("   Tentando localizar o campo de outra forma...")
                all_inputs = page.locator('input[type="text"]')
                logger.info(f"   Total de campos text encontrados: {all_inputs.count()}")
                
                # Mostrar HTML da página
                html_content = page.content()
                with open("/app/page_html.html", "w") as f:
                    f.write(html_content)
                logger.info("   ✅ HTML salvo: page_html.html")
            
            # 4. Preencher e pesquisar
            if processo_field.count() > 0:
                logger.info("5. Preenchendo número do processo...")
                page.fill('input[name="NumPedido"]', numero_processo)
                page.screenshot(path="/app/step5_processo_filled.png")
                logger.info("   ✅ Screenshot salvo: step5_processo_filled.png")
                
                logger.info("6. Clicando em pesquisar...")
                page.click('input[type="submit"][name="botao"]')
                page.wait_for_load_state("networkidle")
                time.sleep(3)
                page.screenshot(path="/app/step6_search_results.png")
                logger.info("   ✅ Screenshot salvo: step6_search_results.png")
                logger.info(f"   URL atual: {page.url}")
                
                # 5. Procurar link de petições
                logger.info("7. Procurando link de petições...")
                peticoes_link = page.locator('a:has-text("Clique aqui para ter acesso as petições do processo")')
                logger.info(f"   Link de petições encontrado: {peticoes_link.count() > 0}")
                
                if peticoes_link.count() > 0:
                    logger.info("8. Clicando no link de petições...")
                    peticoes_link.click()
                    time.sleep(3)
                    page.screenshot(path="/app/step7_peticoes_page.png")
                    logger.info("   ✅ Screenshot salvo: step7_peticoes_page.png")
                    logger.info(f"   URL atual: {page.url}")
                    
                    # Salvar HTML da página de petições
                    html_content = page.content()
                    with open("/app/peticoes_html.html", "w") as f:
                        f.write(html_content)
                    logger.info("   ✅ HTML das petições salvo: peticoes_html.html")
                else:
                    # Salvar HTML da página de resultados
                    html_content = page.content()
                    with open("/app/results_html.html", "w") as f:
                        f.write(html_content)
                    logger.info("   ✅ HTML dos resultados salvo: results_html.html")
            
            logger.info("\n✅ Debug completo! Verifique os screenshots em /app/")
            
        except Exception as e:
            logger.error(f"❌ Erro durante debug: {str(e)}")
            page.screenshot(path="/app/error_screenshot.png")
            logger.info("   ✅ Screenshot de erro salvo: error_screenshot.png")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()

if __name__ == "__main__":
    logger.info("🔍 Iniciando debug do PepiScraper...")
    debug_pepi_navigation()
