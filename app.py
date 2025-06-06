# app.py (VERSÃO FINAL PARA NEON/POSTGRESQL COM SQLALCHEMY)

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
CORS(app) 

# --- CONFIGURAÇÃO ---
# Pega a connection string do Neon a partir das variáveis de ambiente
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "uma-chave-padrao-muito-segura")

db = SQLAlchemy(app)
jwt = JWTManager(app)

# --- MODELOS DO BANCO DE DADOS ---
# Representação das suas tabelas como classes Python
class Professor(db.Model):
    __tablename__ = 'professor' # Garante que o nome da tabela seja minúsculo
    idprofessor = db.Column(db.Integer, primary_key=True)
    nomeprofessor = db.Column(db.String(100), nullable=False)
    cpfprofessor = db.Column(db.String(11), unique=True, nullable=False)
    emailprofessor = db.Column(db.String(100), unique=True, nullable=False)
    senhaprofessor = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(10), nullable=False, default='ativo')

class Aluno(db.Model):
    __tablename__ = 'aluno'
    idaluno = db.Column(db.Integer, primary_key=True)
    nomealuno = db.Column(db.String(100), nullable=False)
    cpfaluno = db.Column(db.String(11), unique=True, nullable=False)
    emailaluno = db.Column(db.String(100), unique=True, nullable=False)
    senhaaluno = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(10), nullable=False, default='ativo')
    moedas = db.Column(db.Integer, nullable=False, default=100)
    nivel = db.Column(db.String(50), nullable=False, default='Iniciante 1')

# --- ROTAS DA API ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', None)
    senha = data.get('senha', None)
    
    # Lógica de Admin (não muda)
    MASTER_EMAIL = os.getenv('MASTER_EMAIL')
    MASTER_PASSWORD = os.getenv('MASTER_PASSWORD')
    if email == MASTER_EMAIL and senha == MASTER_PASSWORD:
        identity = "admin_01"
        additional_claims = {"role": "adm"}
        access_token = create_access_token(identity=identity, additional_claims=additional_claims)
        return jsonify(access_token=access_token, user_role="adm", user_name="Administrador")

    # Busca o professor no banco usando SQLAlchemy
    professor = Professor.query.filter_by(emailprofessor=email).first()
    if professor and check_password_hash(professor.senhaprofessor, senha):
        if professor.status == 'inativo':
            return jsonify({"msg": "Acesso negado: Professor desativado."}), 403
        
        identity = str(professor.idprofessor)
        additional_claims = {"role": "professor"}
        access_token = create_access_token(identity=identity, additional_claims=additional_claims)
        return jsonify(access_token=access_token, user_role="professor", user_name=professor.nomeprofessor)

    # Busca o aluno no banco
    aluno = Aluno.query.filter_by(emailaluno=email).first()
    if aluno and check_password_hash(aluno.senhaaluno, senha):
        if aluno.status == 'inativo':
            return jsonify({"msg": "Acesso negado: Aluno desativado."}), 403

        identity = str(aluno.idaluno)
        additional_claims = {"role": "aluno"}
        access_token = create_access_token(identity=identity, additional_claims=additional_claims)
        return jsonify(access_token=access_token, user_role="aluno", user_name=aluno.nomealuno)

    return jsonify({"msg": "Credenciais inválidas"}), 401

@app.route('/api/cadastrarprofessor', methods=['POST'])
@jwt_required()
def cadastrar_professor():
    claims = get_jwt()
    if claims.get('role') != 'adm':
        return jsonify({"msg": "Acesso negado."}), 403

    data = request.get_json()
    # Verifica se já existe
    if Professor.query.filter_by(emailprofessor=data['emailProfessor']).first() or Professor.query.filter_by(cpfprofessor=data['cpfProfessor']).first():
        return jsonify({"msg": "Já existe um professor com este CPF ou e-mail."}), 409

    hashed_password = generate_password_hash(data['senhaProfessor'])
    novo_professor = Professor(
        nomeprofessor=data['nomeProfessor'],
        cpfprofessor=data['cpfProfessor'],
        emailprofessor=data['emailProfessor'],
        senhaprofessor=hashed_password,
        status='ativo'
    )
    db.session.add(novo_professor)
    db.session.commit()
    
    return jsonify({"msg": f"Professor '{data['nomeProfessor']}' cadastrado com sucesso!"}), 201

# Adicione outras rotas aqui (perfil, etc.) usando a mesma lógica do SQLAlchemy

@app.route('/api/version', methods=['GET'])
def get_version():
    return jsonify({"version": "2.1 - JWT FIX APLICADO"})


if __name__ == '__main__':
    app.run(debug=True, port=5000)