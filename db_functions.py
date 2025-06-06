import mysql.connector
from config import * #importando todas as config

#estabelecer conexao com o db
def conectar_db():
    conexao = mysql.connector.connect(
    host = DB_HOST,
    user = DB_USER,
    password = DB_PASSWORD,
    database = DB_NAME
)
    cursor = conexao.cursor(dictionary=True)
    return conexao, cursor
#cursor = elemento que executa as tarefas, um agente que fara tudo

#encerra conexao com db
def encerrar_db(cursor, conexao):
    cursor.close()
    conexao.close()

def limpar_input(campo):
    campolimpo = campo.replace(".","").replace("/","").replace("-","").replace(" ","").replace("(","").replace(")","").replace("R$","")
    return campolimpo

