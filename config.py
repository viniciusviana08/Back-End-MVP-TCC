import os
from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

SECRET_KEY = os.getenv('SECRET_KEY')

# Credenciais de admin
MASTER_EMAIL = os.getenv('MASTER_EMAIL')
MASTER_PASSWORD = os.getenv('MASTER_PASSWORD')
