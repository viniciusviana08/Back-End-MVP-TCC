# app.py (Versão refatorada para PostgreSQL)

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2 # Importa o driver do PostgreSQL
from psycopg2 import errors # Importa os erros específicos para tratamento
from config import *
from db_functions import *
from flask import current_app
import json as _json
import os

app = Flask(__name__)
CORS(app) 

# Usa a chave secreta carregada do config.py
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
jwt = JWTManager(app)

# --- ROTA DE LOGIN ATUALIZADA (ADM, PROFESSOR E ALUNO) ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', None)
    senha = data.get('senha', None)

    if not email or not senha:
        return jsonify({"msg": "Email e senha são obrigatórios."}), 400

    # 1. Tenta como Administrador (já está correto, "admin_01" é uma string)
    if email == MASTER_EMAIL and senha == MASTER_PASSWORD:
        identity = "admin_01"
        additional_claims = {"role": "adm"}
        access_token = create_access_token(identity=identity, additional_claims=additional_claims)
        return jsonify(access_token=access_token, user_role="adm", user_name="Administrador")

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        
        # 2. Tenta como Professor
        cursor.execute('SELECT idProfessor, nomeProfessor, senhaProfessor, status FROM Professor WHERE emailProfessor = %s', (email,))
        professor = cursor.fetchone()
        if professor and check_password_hash(professor['senhaprofessor'], senha):
            if professor['status'] != 'ativo':
                return jsonify({"msg": "Sua conta de professor está bloqueada."}), 403
            
            # --- CORREÇÃO APLICADA AQUI ---
            # Converte o ID (inteiro) para uma string antes de criar o token
            identity = str(professor['idprofessor']) 
            additional_claims = {"role": "professor"}
            access_token = create_access_token(identity=identity, additional_claims=additional_claims)
            return jsonify(access_token=access_token, user_role="professor", user_name=professor['nomeprofessor'])

        # 3. Tenta como Aluno
        cursor.execute('SELECT idAluno, nomeAluno, senhaAluno, status FROM Aluno WHERE emailAluno = %s', (email,))
        aluno = cursor.fetchone()
        if aluno and check_password_hash(aluno['senhaaluno'], senha):
            if aluno['status'] != 'ativo':
                return jsonify({"msg": "Sua conta de aluno está bloqueada."}), 403

            # --- CORREÇÃO APLICADA AQUI TAMBÉM (BOA PRÁTICA) ---
            # Converte o ID do aluno para string também
            identity = str(aluno['idaluno'])
            additional_claims = {"role": "aluno"}
            access_token = create_access_token(identity=identity, additional_claims=additional_claims)
            return jsonify(access_token=access_token, user_role="aluno", user_name=aluno['nomealuno'])
            
        # 4. Se não encontrou ninguém
        return jsonify({"msg": "Email ou senha inválidos."}), 401

    except psycopg2.Error as e:
        print(f"Erro de Banco de Dados no login: {e}")
        return jsonify({"msg": "Erro interno no servidor."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

# --- ATUALIZAR A ROTA DE CADASTRO DE ALUNO PARA INCLUIR O PROFESSOR ---
@app.route('/api/register/aluno', methods=['POST'])
def register_aluno():
    data = request.get_json()
    nome = data.get('nomeAluno')
    cpf = data.get('cpfAluno')
    email = data.get('emailAluno')
    senha = data.get('senhaAluno')
    id_professor = data.get('idProfessor') # Novo campo recebido

    # Adiciona a validação do novo campo
    if not all([nome, cpf, email, senha, id_professor]):
        return jsonify({"msg": "Todos os campos, incluindo o professor, são obrigatórios"}), 400

    hashed_password = generate_password_hash(senha)
    
    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        # Atualiza o comando SQL para inserir o idProfessor
        comandoSQL = 'INSERT INTO Aluno (nomeAluno, cpfAluno, emailAluno, senhaAluno, status, moedas, nivel, idProfessor) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'
        cursor.execute(comandoSQL, (nome, cpf, email, hashed_password, 'ativo', 100, 'Iniciante 1', id_professor))
        conexao.commit()
        return jsonify({"msg": f"Aluno '{nome}' cadastrado com sucesso! Faça o login para começar."}), 201

    except errors.UniqueViolation:
        conexao.rollback()
        return jsonify({"msg": "Já existe um aluno com este CPF ou e-mail."}), 409
    except psycopg2.Error as e:
        if conexao:
            conexao.rollback()
        print(f"Erro de Banco de Dados ao cadastrar aluno: {e}")
        return jsonify({"msg": "Erro interno no servidor."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

# --- ROTA PARA OBTER DADOS DO PERFIL DO ALUNO LOGADO ---
@app.route('/api/aluno/perfil', methods=['GET'])
@jwt_required()
def get_aluno_perfil():
    # Verifica se o token pertence a um aluno
    claims = get_jwt()
    if claims.get('role') != 'aluno':
        return jsonify({"msg": "Acesso negado. Apenas para alunos."}), 403
    
    # Pega o ID do aluno a partir do token
    aluno_id = get_jwt_identity()

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        cursor.execute('SELECT nomeAluno, emailAluno, moedas, nivel FROM Aluno WHERE idAluno = %s', (aluno_id,))
        aluno_data = cursor.fetchone()
        if not aluno_data:
            return jsonify({"msg": "Aluno não encontrado."}), 404
        
        return jsonify(aluno_data), 200

    except psycopg2.Error as e:
        print(f"Erro de Banco de Dados no perfil do aluno: {e}")
        return jsonify({"msg": "Erro interno no servidor."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

# --- ROTA PARA REGISTRAR UMA ATIVIDADE CONCLUÍDA (VERSÃO MAIS ROBUSTA) ---
@app.route('/api/atividades/completar', methods=['POST'])
@jwt_required()
def completar_atividade():
    claims = get_jwt()
    if claims.get('role') != 'aluno':
        return jsonify({"msg": "Apenas alunos podem completar atividades."}), 403
    
    aluno_id = get_jwt_identity()
    data = request.get_json()
    id_atividade = data.get('idAtividade')
    pontuacao = data.get('pontuacao', 0) # Usa 0 como padrão se não for enviado
    feedback = data.get('feedbackGemini', '') # Usa string vazia como padrão

    if not id_atividade:
        return jsonify({"msg": "ID da atividade é obrigatório."}), 400

    # Lógica de recompensa: 10 moedas base + 1 moeda para cada 10 pontos
    moedas_ganhas = 10 + (pontuacao // 10)

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        
        # 1. Insere na tabela AtividadeFeita
        comando_insert = 'INSERT INTO AtividadeFeita (idAluno, idAtividade, pontuacao, feedback_gemini) VALUES (%s, %s, %s, %s)'
        cursor.execute(comando_insert, (aluno_id, id_atividade, pontuacao, feedback))

        # 2. Atualiza as moedas do aluno e retorna o novo total
        comando_update = 'UPDATE Aluno SET moedas = moedas + %s WHERE idAluno = %s RETURNING moedas'
        cursor.execute(comando_update, (moedas_ganhas, aluno_id))
        
        resultado_update = cursor.fetchone()
        novo_total_moedas = resultado_update['moedas'] if resultado_update else None
        
        conexao.commit()
        
        return jsonify({
            "msg": f"Parabéns! Você ganhou {moedas_ganhas} moedas!",
            "moedasGanhas": moedas_ganhas,
            "novoTotalMoedas": novo_total_moedas
        }), 200

    except psycopg2.Error as e:
        if conexao:
            conexao.rollback()
        print(f"Erro ao completar atividade: {e}")
        return jsonify({"msg": "Erro interno ao salvar seu progresso."}), 500
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

@app.route('/api/professores/lista', methods=['GET'])
def listar_professores_publico():
    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        # Busca apenas professores com status 'ativo'
        cursor.execute("SELECT idProfessor, nomeProfessor FROM Professor WHERE status = 'ativo' ORDER BY nomeProfessor")
        professores = cursor.fetchall()
        return jsonify(professores), 200
    except psycopg2.Error as e:
        print(f"Erro ao listar professores para login: {e}")
        return jsonify({"msg": "Erro ao carregar lista de professores."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

# --- NOVA ROTA PARA O PROFESSOR VER SEUS ALUNOS ---
@app.route('/api/professor/alunos', methods=['GET'])
@jwt_required()
def listar_alunos_do_professor():
    claims = get_jwt()
    if claims.get('role') != 'professor':
        return jsonify({"msg": "Acesso negado. Apenas para professores."}), 403
    
    professor_id = get_jwt_identity()

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        # Busca todos os alunos vinculados a este professor
        comando = "SELECT idAluno, nomeAluno, emailAluno, status, moedas, nivel FROM Aluno WHERE idProfessor = %s ORDER BY nomeAluno"
        cursor.execute(comando, (professor_id,))
        alunos = cursor.fetchall()
        return jsonify(alunos), 200
    except psycopg2.Error as e:
        print(f"Erro ao buscar alunos do professor: {e}")
        return jsonify({"msg": "Erro interno ao buscar alunos."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)


# --- ROTA: PROFESSOR CRIA ATIVIDADE (salva no banco) ---
@app.route('/api/professor/atividades', methods=['POST'])
@jwt_required()
def criar_atividade_professor():
    claims = get_jwt()
    if claims.get('role') != 'professor':
        return jsonify({"msg": "Acesso negado. Apenas professores."}), 403

    professor_id = get_jwt_identity()  # no seu login identity foi string do idProfessor
    # converte pra int se necessário
    try:
        professor_id_int = int(professor_id)
    except:
        professor_id_int = professor_id

    data = request.get_json() or {}
    titulo = data.get('titulo')
    tipo = data.get('tipo')
    descricao = data.get('descricao')
    conteudo = data.get('conteudo_especifico')  # pode ser dict
    icon = data.get('icon', 'file-text')
    turmas = data.get('turmas', [])  # lista

    if not all([titulo, tipo, descricao, conteudo]):
        return jsonify({"msg": "Campos obrigatórios ausentes (titulo, tipo, descricao, conteudo_especifico)."}), 400

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        comando = '''
            INSERT INTO Atividade (titulo, tipo, descricao, conteudo_json, icon, idProfessor, status, turmas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING idAtividade
        '''
        cursor.execute(comando, (
            titulo, tipo, descricao, _json.dumps(conteudo), icon, professor_id_int, 'available', _json.dumps(turmas)
        ))
        novo_id = cursor.fetchone()['idatividade']  # ajuste caso o dict use chave diferente
        conexao.commit()
        return jsonify({"msg": "Atividade criada.", "idAtividade": novo_id}), 201

    except Exception as e:
        if conexao:
            conexao.rollback()
        print("Erro ao criar atividade:", e)
        return jsonify({"msg": "Erro interno ao criar atividade."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

# --- ROTA: RETORNAR ATIVIDADES PARA O ALUNO LOGADO ---
@app.route('/api/aluno/atividades', methods=['GET'])
@jwt_required()
def listar_atividades_para_aluno():
    claims = get_jwt()
    if claims.get('role') != 'aluno':
        return jsonify({"msg": "Acesso negado. Apenas alunos."}), 403

    aluno_id = get_jwt_identity()
    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        # Pega o idProfessor associado ao aluno (coluna idProfessor na tabela Aluno)
        cursor.execute('SELECT idProfessor FROM Aluno WHERE idAluno = %s', (aluno_id,))
        aluno = cursor.fetchone()
        id_prof = aluno['idprofessor'] if aluno else None

        # Seleciona atividades do professor ou públicas (idProfessor is null)
        # Ajuste conforme sua modelagem (por ex. turmas json)
        cursor.execute("""
            SELECT idAtividade, titulo, tipo, descricao, conteudo_json, icon, idProfessor, status, turmas
            FROM Atividade
            WHERE (idProfessor = %s) OR (idProfessor IS NULL)
            ORDER BY idAtividade DESC
        """, (id_prof,))
        rows = cursor.fetchall()
        activities = []
        for r in rows:
            activities.append({
                "id": r['idatividade'],
                "titulo": r['titulo'],
                "tipo": r['tipo'],
                "descricao": r['descricao'],
                "conteudo_especifico": _json.loads(r['conteudo_json']) if r.get('conteudo_json') else None,
                "icon": r.get('icon') or 'puzzle',
                "status": r.get('status') or 'available',
                "turmas": _json.loads(r['turmas']) if r.get('turmas') else []
            })
        return jsonify(activities), 200

    except Exception as e:
        print("Erro ao listar atividades para aluno:", e)
        return jsonify({"msg": "Erro interno ao buscar atividades."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

if __name__ == '__main__':
    # Render usa um servidor WSGI (como Gunicorn), mas isso é bom para testes locais.
    # O Render ignora isso e usa o comando do seu "Build Command".
    app.run(debug=True, port=5000)