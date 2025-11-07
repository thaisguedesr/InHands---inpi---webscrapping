import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

# Configurações SMTP
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'camilla@inhandscomvc.com.br'
SMTP_PASS = 'gmmw hevq znlc fxww'
SMTP_FROM = 'camilla@inhandscomvc.com.br'
SMTP_FROM_NAME = 'InHands'
DEST_EMAIL = 'thais@inhands.com.br'

def enviar_email_notificacao(assunto: str, corpo: str) -> bool:
    """Envia email de notificação"""
    try:
        # Criar mensagem
        msg = MIMEMultipart()
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
        msg['To'] = DEST_EMAIL
        msg['Subject'] = assunto
        
        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
        
        # Conectar e enviar
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        logger.info(f"Email enviado com sucesso para {DEST_EMAIL}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar email: {str(e)}")
        return False