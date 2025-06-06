# app_refatorado.py

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity
# Import para hashing de senha
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import Error
from config import *
from db_functions import *
import os

app = Flask(__name__)
CORS(app) 

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "sua-chave-secreta-super-segura-aqui") 
jwt = JWTManager(app)

# --- ROTA DE LOGIN (ATUALIZADA) ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', None)
    senha = data.get('senha', None)

    if not email or not senha:
        return jsonify({"msg": "Email e senha são obrigatórios"}), 400

    # 1. Tenta como Administrador (lógica especial, não vem do DB)
    if email == MASTER_EMAIL and senha == MASTER_PASSWORD:
        identity_data = {"id": "admin_01", "role": "adm"}
        access_token = create_access_token(identity=identity_data)
        return jsonify(access_token=access_token, user_role="adm", user_name="Administrador")

    try:
        conexao, cursor = conectar_db()
        
        # 2. Tenta como Aluno
        cursor.execute('SELECT idAluno, nomeAluno, senhaAluno, status FROM Aluno WHERE emailAluno = %s', (email,))
        aluno = cursor.fetchone()
        if aluno:
            # IMPORTANTE: Compara a senha enviada com o HASH salvo no banco
            if check_password_hash(aluno['senhaAluno'], senha):
                if aluno['status'] == 'inativo':
                    return jsonify({"msg": "Acesso negado: Aluno desativado."}), 403
                
                identity_data = {"id": aluno['idAluno'], "role": "aluno"}
                access_token = create_access_token(identity=identity_data)
                return jsonify(access_token=access_token, user_role="aluno", user_name=aluno['nomeAluno'])
        
        # 3. Tenta como Professor
        cursor.execute('SELECT idProfessor, nomeProfessor, senhaProfessor, status FROM Professor WHERE emailProfessor = %s', (email,))
        professor = cursor.fetchone()
        if professor:
            # IMPORTANTE: Compara a senha enviada com o HASH salvo no banco
            if check_password_hash(professor['senhaProfessor'], senha):
                if professor['status'] == 'inativo':
                    return jsonify({"msg": "Acesso negado: Professor desativado."}), 403

                identity_data = {"id": professor['idProfessor'], "role": "professor"}
                access_token = create_access_token(identity=identity_data)
                return jsonify(access_token=access_token, user_role="professor", user_name=professor['nomeProfessor'])
        
        # 4. Se não encontrou ou a senha estava errada
        return jsonify({"msg": "Credenciais inválidas"}), 401

    except Error as e:
        print(f"Erro de Banco de Dados: {e}")
        return jsonify({"msg": "Erro interno no servidor"}), 500
    finally:
        if 'cursor' in locals() and cursor:
            encerrar_db(cursor, conexao)

# --- ROTA DE CADASTRO DE PROFESSOR (ATUALIZADA) ---
@app.route('/api/cadastrarprofessor', methods=['POST'])
@jwt_required()
def cadastrar_professor():
    current_user = get_jwt_identity()
    if current_user.get('role') != 'adm':
        return jsonify({"msg": "Acesso negado. Apenas administradores podem realizar esta ação."}), 403

    data = request.get_json()
    nome = data.get('nomeProfessor')
    cpf = data.get('cpfProfessor')
    email = data.get('emailProfessor')
    senha = data.get('senhaProfessor')

    if not all([nome, cpf, email, senha]):
        return jsonify({"msg": "Nome, CPF, email e senha são obrigatórios"}), 400

    # IMPORTANTE: Gera o hash da senha antes de salvar no banco
    hashed_password = generate_password_hash(senha)

    try:
        conexao, cursor = conectar_db()
        # Colunas atualizadas para corresponder ao seu schema
        comandoSQL = 'INSERT INTO Professor (nomeProfessor, cpfProfessor, emailProfessor, senhaProfessor) VALUES (%s, %s, %s, %s)'
        cursor.execute(comandoSQL, (nome, cpf, email, hashed_password))
        conexao.commit()
        return jsonify({"msg": f"Professor '{nome}' cadastrado com sucesso!"}), 201

    except Error as e:
        if e.errno == 1062: # Erro de entrada duplicada (para CPF ou Email)
            return jsonify({"msg": "Já existe um professor com este CPF ou e-mail."}), 409
        print(f"Erro de Banco de Dados ao cadastrar professor: {e}")
        return jsonify({"msg": "Erro interno no servidor ao processar o cadastro."}), 500
    finally:
        if 'cursor' in locals() and cursor:
            encerrar_db(cursor, conexao)

# --- ROTA DE PERFIL (EXEMPLO ATUALIZADO) ---
@app.route('/api/perfil', methods=['GET'])
@jwt_required()
def get_perfil():
    current_user = get_jwt_identity()
    user_id = current_user['id']
    user_role = current_user['role']

    if user_role == 'aluno':
        try:
            conexao, cursor = conectar_db()
            # Buscando os dados que o seu front-end precisa
            cursor.execute('SELECT nomeAluno, emailAluno, moedas, nivel FROM Aluno WHERE idAluno = %s', (user_id,))
            aluno_data = cursor.fetchone()
            if aluno_data:
                return jsonify(aluno_data)
            return jsonify({"msg": "Aluno não encontrado"}), 404
        except Error as e:
            return jsonify({"msg": f"Erro de banco de dados: {e}"}), 500
        finally:
            if 'cursor' in locals() and cursor:
                encerrar_db(cursor, conexao)
    
    # Adicionar lógica para 'professor' e 'adm' se necessário
    return jsonify({"msg": f"Perfil do tipo '{user_role}' acessado."})

if __name__ == '__main__':
    app.run(debug=True, port=5000)