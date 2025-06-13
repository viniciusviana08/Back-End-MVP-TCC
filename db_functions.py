import psycopg2
from psycopg2.extras import RealDictCursor
from config import *

def conectar_db():
    conexao = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    return conexao, cursor

def encerrar_db(cursor, conexao):
    cursor.close()
    conexao.close()
