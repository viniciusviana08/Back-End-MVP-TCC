# app.py (Versão refatorada para PostgreSQL)

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2 # Importa o driver do PostgreSQL
from psycopg2 import errors # Importa os erros específicos para tratamento
from config import *
from db_functions import *
import os

app = Flask(__name__)
CORS(app) 

# Usa a chave secreta carregada do config.py
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
jwt = JWTManager(app)

# --- ROTA DE LOGIN ATUALIZADA (PARA ADM E PROFESSOR) ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', None)
    senha = data.get('senha', None)

    if not email or not senha:
        return jsonify({"msg": "Email e senha são obrigatórios."}), 400

    # 1. Tenta o login como Administrador
    if email == MASTER_EMAIL and senha == MASTER_PASSWORD:
        identity = "admin_01"
        additional_claims = {"role": "adm"}
        access_token = create_access_token(identity=identity, additional_claims=additional_claims)
        return jsonify(access_token=access_token, user_role="adm", user_name="Administrador")

    # 2. Se não for admin, tenta o login como Professor
    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        # Busca o professor pelo email
        cursor.execute('SELECT idProfessor, nomeProfessor, emailProfessor, senhaProfessor, status FROM Professor WHERE emailProfessor = %s', (email,))
        professor = cursor.fetchone()

        # Verifica se o professor existe, se a senha está correta e se o status é 'ativo'
        if professor and check_password_hash(professor['senhaprofessor'], senha):
            if professor['status'] != 'ativo':
                return jsonify({"msg": "Sua conta está bloqueada. Contate o administrador."}), 403

            # Se tudo estiver correto, cria o token para o professor
            identity = professor['idprofessor']
            additional_claims = {"role": "professor"}
            access_token = create_access_token(identity=identity, additional_claims=additional_claims)
            
            return jsonify(
                access_token=access_token, 
                user_role="professor", 
                user_name=professor['nomeprofessor']
            )

        # 3. Se não encontrou nem admin, nem professor válido
        return jsonify({"msg": "Email ou senha inválidos."}), 401

    except psycopg2.Error as e:
        print(f"Erro de Banco de Dados no login: {e}")
        return jsonify({"msg": "Erro interno no servidor durante o login."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

# --- ROTA DE CADASTRO DE Professor (ATUALIZADA) ---
# CORREÇÃO: A rota foi alterada para corresponder ao fetch() do frontend
@app.route('/api/professor', methods=['POST'])
@jwt_required()
def cadastrar_professor():
    claims = get_jwt()
    user_role = claims.get('role')

    if user_role != 'adm':
        return jsonify({"msg": "Acesso negado. Apenas administradores podem realizar esta ação."}), 403

    data = request.get_json()
    nome = data.get('nomeProfessor')
    cpf = data.get('cpfProfessor')
    email = data.get('emailProfessor')
    senha = data.get('senhaProfessor')

    if not all([nome, cpf, email, senha]):
        return jsonify({"msg": "Nome, CPF, email e senha são obrigatórios"}), 400

    hashed_password = generate_password_hash(senha)
    
    # Inicializa as variáveis de conexão fora do try para estarem disponíveis no finally
    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        # O placeholder %s funciona da mesma forma com psycopg2, o que é ótimo!
        comandoSQL = 'INSERT INTO Professor (nomeProfessor, cpfProfessor, emailProfessor, senhaProfessor, status) VALUES (%s, %s, %s, %s, %s)'
        cursor.execute(comandoSQL, (nome, cpf, email, hashed_password, 'ativo'))
        conexao.commit()
        return jsonify({"msg": f"Professor '{nome}' cadastrado com sucesso!"}), 201

    except errors.UniqueViolation as e:
        # CORREÇÃO: Tratamento de erro específico para chave duplicada no PostgreSQL
        conexao.rollback() # Desfaz a transação em caso de erro
        return jsonify({"msg": "Já existe um professor com este CPF ou e-mail."}), 409
    except psycopg2.Error as e:
        # Captura outros erros do banco de dados
        if conexao:
            conexao.rollback()
        print(f"Erro de Banco de Dados ao cadastrar professor: {e}")
        return jsonify({"msg": "Erro interno no servidor ao processar o cadastro."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)



@app.route('/api/aluno', methods=['POST'])
@jwt_required()
def cadastrar_aluno():
    claims = get_jwt()
    user_role = claims.get('role')

    if user_role != 'aluno':
        return jsonify({"msg": "Acesso negado. Apenas alunos podem realizar esta ação."}), 403

    data = request.get_json()
    nome = data.get('nomeAluno')
    cpf = data.get('cpfAluno')
    email = data.get('emailAluno')
    senha = data.get('senhaAluno')

    if not all([nome, cpf, email, senha]):
        return jsonify({"msg": "Nome, CPF, email e senha são obrigatórios"}), 400

    hashed_password = generate_password_hash(senha)
    
    # Inicializa as variáveis de conexão fora do try para estarem disponíveis no finally
    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        # O placeholder %s funciona da mesma forma com psycopg2, o que é ótimo!
        comandoSQL = 'INSERT INTO Aluno (nomeAluno, cpfAluno, emailAluno, senhaAluno, status) VALUES (%s, %s, %s, %s, %s)'
        cursor.execute(comandoSQL, (nome, cpf, email, hashed_password, 'ativo'))
        conexao.commit()
        return jsonify({"msg": f"Aluno '{nome}' cadastrado com sucesso!"}), 201

    except errors.UniqueViolation as e:
        # CORREÇÃO: Tratamento de erro específico para chave duplicada no PostgreSQL
        conexao.rollback() # Desfaz a transação em caso de erro
        return jsonify({"msg": "Já existe um Aluno com este CPF ou e-mail."}), 409
    except psycopg2.Error as e:
        # Captura outros erros do banco de dados
        if conexao:
            conexao.rollback()
        print(f"Erro de Banco de Dados ao cadastrar Aluno: {e}")
        return jsonify({"msg": "Erro interno no servidor ao processar o cadastro."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

# --- ROTA PARA LISTAR TODOS OS PROFESSORES ---
@app.route('/api/professores', methods=['GET'])
@jwt_required()
def listar_professores():
    # Verifica se o usuário tem a permissão de administrador
    claims = get_jwt()
    user_role = claims.get('role')
    if user_role != 'adm':
        return jsonify({"msg": "Acesso negado. Apenas administradores podem ver a lista."}), 403

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        
        # Seleciona as colunas importantes da tabela Professor, ordenando por nome
        comandoSQL = 'SELECT idProfessor, nomeProfessor, emailProfessor, status FROM Professor ORDER BY nomeProfessor'
        cursor.execute(comandoSQL)
        professores = cursor.fetchall() # Pega todos os resultados

        # Retorna a lista de professores em formato JSON
        return jsonify(professores), 200

    except psycopg2.Error as e:
        print(f"Erro de Banco de Dados ao listar professores: {e}")
        return jsonify({"msg": "Erro interno no servidor ao buscar professores."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)


# --- ROTA PARA EXCLUIR UM PROFESSOR ---
@app.route('/api/professores/<int:id>', methods=['DELETE'])
@jwt_required()
def deletar_professor(id):
    # Proteção de administrador
    claims = get_jwt()
    if claims.get('role') != 'adm':
        return jsonify({"msg": "Acesso negado."}), 403

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        # Primeiro, verifica se o professor existe
        cursor.execute('SELECT * FROM Professor WHERE idProfessor = %s', (id,))
        professor = cursor.fetchone()
        if not professor:
            return jsonify({"msg": "Professor não encontrado."}), 404

        # Se existe, executa o comando de exclusão
        cursor.execute('DELETE FROM Professor WHERE idProfessor = %s', (id,))
        conexao.commit()
        
        return jsonify({"msg": f"Professor '{professor['nomeprofessor']}' excluído com sucesso."}), 200

    except psycopg2.Error as e:
        if conexao:
            conexao.rollback()
        print(f"Erro de Banco de Dados ao deletar professor: {e}")
        return jsonify({"msg": "Erro interno no servidor ao deletar professor."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

# --- ROTA PARA ALTERAR O STATUS DE UM PROFESSOR ---
@app.route('/api/professores/<int:id>/status', methods=['PATCH'])
@jwt_required()
def mudar_status_professor(id):
    # Proteção de administrador
    claims = get_jwt()
    if claims.get('role') != 'adm':
        return jsonify({"msg": "Acesso negado."}), 403

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        # Busca o professor e seu status atual
        cursor.execute('SELECT status FROM Professor WHERE idProfessor = %s', (id,))
        professor = cursor.fetchone()
        if not professor:
            return jsonify({"msg": "Professor não encontrado."}), 404
        
        # Determina o novo status
        status_atual = professor['status']
        novo_status = 'bloqueado' if status_atual == 'ativo' else 'ativo'
        
        # Atualiza o status no banco de dados
        cursor.execute('UPDATE Professor SET status = %s WHERE idProfessor = %s', (novo_status, id))
        conexao.commit()
        
        return jsonify({"msg": f"Status alterado para '{novo_status}'.", "novoStatus": novo_status}), 200

    except psycopg2.Error as e:
        if conexao:
            conexao.rollback()
        print(f"Erro de Banco de Dados ao alterar status: {e}")
        return jsonify({"msg": "Erro interno no servidor ao alterar status."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

if __name__ == '__main__':
    # Render usa um servidor WSGI (como Gunicorn), mas isso é bom para testes locais.
    # O Render ignora isso e usa o comando do seu "Build Command".
    app.run(debug=True, port=5000)