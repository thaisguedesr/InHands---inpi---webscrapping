#!/usr/bin/env python3
"""
Script de teste para o PepiScraper com resolução de CAPTCHA via CapMonster
"""
import sys
sys.path.append('/app/backend')

from scrapers.pepi_scraper import PepiScraper
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_pepi_scraper():
    """Testa o PepiScraper com um número de processo real"""
    
    # Números de processo para testar (fornecidos pelo usuário anteriormente)
    processos_teste = [
        "928223068",
        "927960690",
        "926941951"
    ]
    
    scraper = PepiScraper()
    
    for numero_processo in processos_teste:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testando processo: {numero_processo}")
        logger.info(f"{'='*80}\n")
        
        try:
            resultado = scraper.buscar_processo_e_extrair_dados(numero_processo)
            
            logger.info(f"\n📊 RESULTADO para processo {numero_processo}:")
            logger.info(f"  MARCA: {resultado.get('marca')}")
            logger.info(f"  EMAIL: {resultado.get('email')}")
            
            if resultado.get('marca') or resultado.get('email'):
                logger.info("✅ Sucesso! Dados extraídos.")
                return True
            else:
                logger.warning("⚠️  Nenhum dado foi extraído")
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar {numero_processo}: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Tentar apenas um por vez para não gastar muito tempo/créditos
        break
    
    return False

if __name__ == "__main__":
    logger.info("🚀 Iniciando teste do PepiScraper com CapMonster...")
    success = test_pepi_scraper()
    
    if success:
        logger.info("\n✅ Teste concluído com sucesso!")
    else:
        logger.warning("\n⚠️  Teste concluído mas sem dados extraídos")
