# app.py (VERSÃO FINAL E CORRETA - SUBSTITUA TODO O SEU ARQUIVO POR ESTE)

from flask import Flask, request, jsonify
from flask_cors import CORS
# Importa a função get_jwt para acessar claims customizadas
from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import Error
from config import *
from db_functions import *
import os

app = Flask(__name__)
CORS(app) 

# Lê a chave secreta do config.py, que por sua vez lê do .env
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
jwt = JWTManager(app)

# --- ROTA DE LOGIN (COM A CORREÇÃO JWT) ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', None)
    senha = data.get('senha', None)

    if not email or not senha:
        return jsonify({"msg": "Email e senha são obrigatórios"}), 400

    if email == MASTER_EMAIL and senha == MASTER_PASSWORD:
        # CORREÇÃO APLICADA: identity é uma string, role vai para claims.
        identity = "admin_01"
        additional_claims = {"role": "adm"}
        access_token = create_access_token(identity=identity, additional_claims=additional_claims)
        return jsonify(access_token=access_token, user_role="adm", user_name="Administrador")

    try:
        conexao, cursor = conectar_db()
        
        cursor.execute('SELECT idAluno, nomeAluno, senhaAluno, status FROM Aluno WHERE emailAluno = %s', (email,))
        aluno = cursor.fetchone()
        if aluno:
            if check_password_hash(aluno['senhaAluno'], senha):
                if aluno['status'] == 'inativo':
                    return jsonify({"msg": "Acesso negado: Aluno desativado."}), 403
                
                # CORREÇÃO APLICADA: identity é o ID como string, role vai para claims.
                identity = str(aluno['idAluno'])
                additional_claims = {"role": "aluno"}
                access_token = create_access_token(identity=identity, additional_claims=additional_claims)
                return jsonify(access_token=access_token, user_role="aluno", user_name=aluno['nomeAluno'])
        
        cursor.execute('SELECT idProfessor, nomeProfessor, senhaProfessor, status FROM Professor WHERE emailProfessor = %s', (email,))
        professor = cursor.fetchone()
        if professor:
            if check_password_hash(professor['senhaProfessor'], senha):
                if professor['status'] == 'inativo':
                    return jsonify({"msg": "Acesso negado: Professor desativado."}), 403

                # CORREÇÃO APLICADA: identity é o ID como string, role vai para claims.
                identity = str(professor['idProfessor'])
                additional_claims = {"role": "professor"}
                access_token = create_access_token(identity=identity, additional_claims=additional_claims)
                return jsonify(access_token=access_token, user_role="professor", user_name=professor['nomeProfessor'])
        
        return jsonify({"msg": "Credenciais inválidas"}), 401

    except Error as e:
        print(f"Erro de Banco de Dados: {e}")
        return jsonify({"msg": "Erro interno no servidor"}), 500
    finally:
        if 'cursor' in locals() and cursor:
            encerrar_db(cursor, conexao)

# --- ROTA DE CADASTRO DE PROFESSOR (COM A CORREÇÃO DO INSERT) ---
@app.route('/api/cadastrarprofessor', methods=['POST'])
@jwt_required()
def cadastrar_professor():
    # ... (código de verificação do admin e coleta de dados permanece o mesmo) ...
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

    try:
        conexao, cursor = conectar_db()
        
        # --- ALTERAÇÃO AQUI ---
        # Adicionamos a coluna 'status' ao comando SQL.
        comandoSQL = 'INSERT INTO Professor (nomeProfessor, cpfProfessor, emailProfessor, senhaProfessor, status) VALUES (%s, %s, %s, %s, %s)'
        
        # E adicionamos o valor 'ativo' à lista de parâmetros.
        cursor.execute(comandoSQL, (nome, cpf, email, hashed_password, 'ativo'))
        # --- FIM DA ALTERAÇÃO ---

        conexao.commit()
        return jsonify({"msg": f"Professor '{nome}' cadastrado com sucesso!"}), 201

    except Error as e:
        if e.errno == 1062:
            return jsonify({"msg": "Já existe um professor com este CPF ou e-mail."}), 409
        print(f"Erro de Banco de Dados ao cadastrar professor: {e}")
        return jsonify({"msg": "Erro interno no servidor ao processar o cadastro."}), 500
    finally:
        if 'cursor' in locals() and cursor:
            encerrar_db(cursor, conexao)

# --- ROTA DE PERFIL (COM A CORREÇÃO JWT) ---
@app.route('/api/perfil', methods=['GET'])
@jwt_required()
def get_perfil():
    # CORREÇÃO APLICADA: get_jwt_identity() retorna o ID, get_jwt() pega a role.
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get('role')

    if user_role == 'aluno':
        try:
            conexao, cursor = conectar_db()
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
    
    return jsonify({"msg": f"Perfil do tipo '{user_role}' acessado."})

@app.route('/api/version', methods=['GET'])
def get_version():
    return jsonify({"version": "2.1 - JWT FIX APLICADO"})


if __name__ == '__main__':
    app.run(debug=True, port=5000)