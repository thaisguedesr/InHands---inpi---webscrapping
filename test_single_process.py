#!/usr/bin/env python3
"""
Teste simples de um único processo
"""
import sys
sys.path.append('/app/backend')

from scrapers.pepi_scraper import PepiScraper
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    scraper = PepiScraper()
    
    # Testar com o processo que sabemos que funciona
    processo = "907206638"
    
    logger.info(f"🔍 Testando processo: {processo}")
    logger.info("="*80)
    
    resultado = scraper.buscar_processo_e_extrair_dados(processo)
    
    logger.info("="*80)
    logger.info(f"📊 RESULTADO FINAL:")
    logger.info(f"  Processo: {processo}")
    logger.info(f"  MARCA: {resultado.get('marca')}")
    logger.info(f"  EMAIL: {resultado.get('email')}")
    
    if resultado.get('marca') and resultado.get('email'):
        logger.info("\n✅ SUCESSO TOTAL! MARCA e EMAIL extraídos!")
    elif resultado.get('marca') or resultado.get('email'):
        logger.info("\n⚠️  Parcial - Apenas um dos campos foi extraído")
    else:
        logger.info("\n❌ Nenhum dado extraído")

if __name__ == "__main__":
    main()
