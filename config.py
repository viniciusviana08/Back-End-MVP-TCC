# config.py (Versão corrigida e segura para PostgreSQL)

import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()

# Lendo a URL de conexão do banco de dados a partir das variáveis de ambiente
DATABASE_URL = os.getenv('DATABASE_URL')

# Lendo o acesso do admin a partir das variáveis de ambiente
MASTER_EMAIL = os.getenv('MASTER_EMAIL', 'admin@adm')
MASTER_PASSWORD = os.getenv('MASTER_PASSWORD')

# A chave secreta do JWT também deve vir do ambiente
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

# Verificações de segurança para garantir que as variáveis críticas foram configuradas
if not DATABASE_URL or not MASTER_PASSWORD or not JWT_SECRET_KEY:
    raise ValueError("Erro Crítico: DATABASE_URL, MASTER_PASSWORD, ou JWT_SECRET_KEY não foram definidas no arquivo .env!")