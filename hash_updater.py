from werkzeug.security import generate_password_hash
from db_functions import conectar_db, encerrar_db # Reutilize suas funções!
from mysql.connector import Error

def update_passwords():
    """
    Este script atualiza as senhas de todos os alunos e professores
    para uma senha temporária 'mudar123', salvando o hash no banco.
    """
    try:
        conexao, cursor = conectar_db()
        print("Conectado ao banco de dados...")

        # --- Atualizar senhas dos Alunos ---
        cursor.execute("SELECT idAluno, senhaAluno FROM Aluno")
        alunos = cursor.fetchall()
        print(f"Encontrados {len(alunos)} alunos para atualizar.")

        for aluno in alunos:
            # Verifica se a senha já é um hash longo. Se for, pula.
            if len(aluno['senhaAluno']) > 60:
                print(f"Senha do Aluno ID {aluno['idAluno']} já parece ser um hash. Pulando.")
                continue
            
            # Gera o hash da senha temporária
            hashed_password = generate_password_hash('mudar123')
            
            # Atualiza no banco
            update_query = "UPDATE Aluno SET senhaAluno = %s WHERE idAluno = %s"
            cursor.execute(update_query, (hashed_password, aluno['idAluno']))
            print(f"Senha do Aluno ID {aluno['idAluno']} atualizada.")

        # --- Atualizar senhas dos Professores ---
        cursor.execute("SELECT idProfessor, senhaProfessor FROM Professor")
        professores = cursor.fetchall()
        print(f"\nEncontrados {len(professores)} professores para atualizar.")
        
        for prof in professores:
            if len(prof['senhaProfessor']) > 60:
                print(f"Senha do Professor ID {prof['idProfessor']} já parece ser um hash. Pulando.")
                continue

            hashed_password = generate_password_hash('mudar123')
            update_query = "UPDATE Professor SET senhaProfessor = %s WHERE idProfessor = %s"
            cursor.execute(update_query, (hashed_password, prof['idProfessor']))
            print(f"Senha do Professor ID {prof['idProfessor']} atualizada.")

        # Confirma as mudanças no banco de dados
        conexao.commit()
        print("\nAtualização de senhas concluída com sucesso!")

    except Error as e:
        print(f"Ocorreu um erro de banco de dados: {e}")
    finally:
        if 'conexao' in locals() and conexao.is_connected():
            encerrar_db(cursor, conexao)
            print("Conexão com o banco de dados encerrada.")

if __name__ == '__main__':
    update_passwords()