from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

scheduler = None

def executar_scraping_sync(scraper):
    """Wrapper síncrono para executar scraping assíncrono"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scraper.executar_scraping())
        loop.close()
    except Exception as e:
        logger.error(f"Erro no job agendado: {str(e)}")

def start_scheduler(scraper):
    """Inicia o scheduler com execução toda terça-feira às 08:00"""
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler já está rodando")
        return
    
    scheduler = BackgroundScheduler(timezone='America/Sao_Paulo')
    
    # Agendar para toda terça-feira às 08:00 (horário de Brasília)
    # day_of_week: 0=Segunda, 1=Terça, 2=Quarta...
    scheduler.add_job(
        executar_scraping_sync,
        trigger=CronTrigger(day_of_week=1, hour=8, minute=0),
        args=[scraper],
        id='inpi_scraping',
        name='INPI Scraping - Terça 08:00',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler iniciado - Próxima execução: Terça-feira às 08:00 (Brasília)")
    
    # Log da próxima execução
    job = scheduler.get_job('inpi_scraping')
    if job and job.next_run_time:
        logger.info(f"Próxima execução agendada para: {job.next_run_time}")

def stop_scheduler():
    """Para o scheduler"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler parado")