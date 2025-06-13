import psycopg2
from psycopg2.extras import RealDictCursor # Importante para obter resultados como dicionários
from config import DATABASE_URL # Importando a URL de conexão

# Estabelecer conexão com o banco de dados PostgreSQL
def conectar_db():
    # psycopg2.connect usa a URL diretamente, o que simplifica a conexão
    conexao = psycopg2.connect(DATABASE_URL)
    # Usamos RealDictCursor para que os resultados das queries venham como dicionários
    # (Ex: {'nomeProfessor': 'Ana', 'emailProfessor': 'ana@email.com'})
    # Isso é o equivalente ao 'dictionary=True' do mysql.connector
    cursor = conexao.cursor(cursor_factory=RealDictCursor)
    return conexao, cursor

# Encerrar conexão com o db
def encerrar_db(cursor, conexao):
    cursor.close()
    conexao.close()

# Esta função não precisa de alteração
def limpar_input(campo):
    campolimpo = campo.replace(".","").replace("/","").replace("-","").replace(" ","").replace("(","").replace(")","").replace("R$","")
    return campolimpo