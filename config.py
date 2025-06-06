# config.py (Versão corrigida e segura)

import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()

# Lendo as credenciais do banco de dados a partir das variáveis de ambiente
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD') # Não coloque um valor padrão para senhas
DB_NAME = os.getenv('DB_NAME', 'ortofix')

# Lendo o acesso do admin a partir das variáveis de ambiente
MASTER_EMAIL = os.getenv('MASTER_EMAIL', 'admin@adm')
MASTER_PASSWORD = os.getenv('MASTER_PASSWORD')

# A chave secreta do JWT também deve vir do ambiente
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

# Verificações de segurança para garantir que as senhas foram configuradas no .env
if not DB_PASSWORD or not MASTER_PASSWORD or not JWT_SECRET_KEY:
    raise ValueError("Erro Crítico: Variáveis de ambiente de senha/chave secreta não foram definidas no arquivo .env!")