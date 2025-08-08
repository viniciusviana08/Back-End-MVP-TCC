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

# --- ROTA DE LOGIN (Sem alterações, já estava correta) ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', None)
    senha = data.get('senha', None)

    if not email or not senha:
        return jsonify({"msg": "Email e senha são obrigatórios"}), 400

    if email == MASTER_EMAIL and senha == MASTER_PASSWORD:
        identity = "admin_01"
        additional_claims = {"role": "adm"}
        access_token = create_access_token(identity=identity, additional_claims=additional_claims)
        return jsonify(access_token=access_token, user_role="adm", user_name="Administrador")
    else:
        return jsonify({"msg": "Credenciais inválidas ou usuário não é admin."}), 401

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

# --- OUTRAS ROTAS ---
# A rota de perfil e outras que usam conectar_db() funcionarão automaticamente
# desde que as tabelas correspondentes (ex: Aluno) existam no banco de dados.
# ... (resto do seu código, se houver) ...


if __name__ == '__main__':
    # Render usa um servidor WSGI (como Gunicorn), mas isso é bom para testes locais.
    # O Render ignora isso e usa o comando do seu "Build Command".
    app.run(debug=True, port=5000)