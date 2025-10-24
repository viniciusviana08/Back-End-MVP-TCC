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
    idProfessor = data.get('idProfessor', None)
    anoAluno = data.get('anoAluno') # NOVO: Captura o ano do aluno

    if not nome or not cpf or not email or not senha or not anoAluno: # NOVO: Valida se o ano foi enviado
        return jsonify({"msg": "Nome, CPF, email, senha e ano são obrigatórios."}), 400

    conexao, cursor = None, None
    try:
        conexao, cursor = conectar_db()
        
        # Hash da senha
        hashed_senha = generate_password_hash(senha)

        # Verificar se email ou CPF já existem
        cursor.execute("SELECT idAluno FROM Aluno WHERE emailAluno = %s OR cpfAluno = %s;", (email, cpf))
        if cursor.fetchone():
            return jsonify({"msg": "Email ou CPF já cadastrados."}), 409

        # Inserir o novo aluno, incluindo o anoAluno
        cursor.execute(
            """
            INSERT INTO Aluno (nomeAluno, cpfAluno, emailAluno, senhaAluno, idProfessor, anoAluno)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING idAluno;
            """,
            (nome, limpar_input(cpf), email, hashed_senha, idProfessor, anoAluno) # NOVO: Adiciona a variável anoAluno aqui
        )
        
        id_novo_aluno = cursor.fetchone()['idaluno']
        conexao.commit()
        
        return jsonify({
            "msg": "Aluno cadastrado com sucesso!",
            "idAluno": id_novo_aluno
        }), 201

    except errors.UniqueViolation as e:
        conexao.rollback()
        return jsonify({"msg": "Erro: Já existe um cadastro com este email ou CPF."}), 409
    except Exception as e:
        print(f"Erro ao cadastrar aluno: {e}")
        if conexao:
            conexao.rollback()
        return jsonify({"msg": "Erro interno do servidor ao cadastrar."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)


# --- ROTA PARA OBTER DADOS DO PERFIL DO ALUNO LOGADO (VERSÃO COMPLETA) ---
@app.route('/api/aluno/perfil', methods=['GET'])
@jwt_required()
def get_aluno_perfil():
    claims = get_jwt()
    if claims.get('role') != 'aluno':
        return jsonify({"msg": "Acesso negado. Apenas para alunos."}), 403
    
    aluno_id = get_jwt_identity()
    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        
        # Query principal para pegar dados do aluno e nome do professor
        query_aluno = """
            SELECT 
                a.nomeAluno, a.emailAluno, a.moedas, a.nivel, a.anoAluno, a.urlFotoPerfil,
                p.nomeProfessor
            FROM Aluno a
            LEFT JOIN Professor p ON a.idProfessor = p.idProfessor
            WHERE a.idAluno = %s
        """
        cursor.execute(query_aluno, (aluno_id,))
        aluno_data = cursor.fetchone()

        if not aluno_data:
            return jsonify({"msg": "Aluno não encontrado."}), 404
            
        # Query secundária para calcular estatísticas de progresso
        query_progresso = """
            SELECT 
                COUNT(*) AS total_atividades, 
                AVG(pontuacao) AS media_pontuacao
            FROM AtividadeFeita
            WHERE idAluno = %s
        """
        cursor.execute(query_progresso, (aluno_id,))
        progresso_data = cursor.fetchone()

        # Adiciona os dados de progresso ao dicionário principal
        aluno_data['total_atividades_concluidas'] = progresso_data['total_atividades'] or 0
        # Formata a média para um número inteiro
        aluno_data['media_geral'] = int(progresso_data['media_pontuacao']) if progresso_data['media_pontuacao'] else 0

        return jsonify(aluno_data), 200

    except psycopg2.Error as e:
        print(f"Erro de Banco de Dados no perfil do aluno: {e}")
        return jsonify({"msg": "Erro interno no servidor."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

# --- ROTA PARA ATUALIZAR DADOS DO PERFIL DO ALUNO ---
@app.route('/api/aluno/perfil', methods=['PUT'])
@jwt_required()
def update_aluno_perfil():
    claims = get_jwt()
    if claims.get('role') != 'aluno':
        return jsonify({"msg": "Acesso negado."}), 403
    
    aluno_id = get_jwt_identity()
    data = request.get_json()
    novo_nome = data.get('nome')

    if not novo_nome:
        return jsonify({"msg": "O nome não pode ser vazio."}), 400

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        cursor.execute('UPDATE Aluno SET nomeAluno = %s WHERE idAluno = %s', (novo_nome, aluno_id))
        conexao.commit()
        
        return jsonify({"msg": "Nome atualizado com sucesso!", "novoNome": novo_nome}), 200

    except psycopg2.Error as e:
        if conexao: conexao.rollback()
        print(f"Erro ao atualizar perfil do aluno: {e}")
        return jsonify({"msg": "Erro interno ao atualizar perfil."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)
            
# --- ROTA PARA "UPLOAD" DE FOTO DO ALUNO ---
# Versão simplificada que apenas salva a URL da imagem.
@app.route('/api/aluno/perfil/foto', methods=['POST'])
@jwt_required()
def update_aluno_foto():
    claims = get_jwt()
    if claims.get('role') != 'aluno':
        return jsonify({"msg": "Acesso negado."}), 403
    
    aluno_id = get_jwt_identity()
    data = request.get_json()
    url_foto = data.get('urlFoto') # Espera uma URL da imagem em base64

    if not url_foto:
        return jsonify({"msg": "URL da foto é obrigatória."}), 400

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        cursor.execute('UPDATE Aluno SET urlFotoPerfil = %s WHERE idAluno = %s', (url_foto, aluno_id))
        conexao.commit()
        return jsonify({"msg": "Foto de perfil atualizada!"}), 200

    except psycopg2.Error as e:
        if conexao: conexao.rollback()
        return jsonify({"msg": "Erro interno ao salvar a foto."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

@app.route('/api/atividades/completar', methods=['POST'])
@jwt_required()
def completar_atividade():
    claims = get_jwt()
    if claims.get('role') != 'aluno':
        return jsonify({"msg": "Apenas alunos podem completar atividades."}), 403
    
    aluno_id = get_jwt_identity()
    data = request.get_json()
    id_atividade = data.get('idAtividade')
    pontuacao = data.get('pontuacao', 0)
    feedback = data.get('feedback', '')

    if not id_atividade:
        return jsonify({"msg": "ID da atividade é obrigatório."}), 400

    # Lógica de recompensa: 10 moedas base + 1 moeda para cada 10 pontos
    moedas_ganhas = 10 + (pontuacao // 10)

    # CORREÇÃO: Garante que idAtividade seja int
    try:
        id_atividade = int(id_atividade)
    except ValueError:
        return jsonify({"msg": "ID da atividade inválido."}), 400

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        
        # 1. Insere na tabela AtividadeFeita para registrar o progresso
        comando_insert = 'INSERT INTO AtividadeFeita (idAluno, idAtividade, pontuacao, feedback_gemini) VALUES (%s, %s, %s, %s)'
        cursor.execute(comando_insert, (aluno_id, id_atividade, pontuacao, feedback))

        # 2. Atualiza as moedas do aluno e retorna o novo total
        comando_update = 'UPDATE Aluno SET moedas = moedas + %s WHERE idAluno = %s RETURNING moedas'
        cursor.execute(comando_update, (moedas_ganhas, aluno_id))
        
        resultado_update = cursor.fetchone()
        novo_total_moedas = resultado_update['moedas'] if resultado_update else None
        
        conexao.commit()
        print(f"Moedas ganhas: {moedas_ganhas} para aluno {aluno_id} na atividade {id_atividade}")  # Log para debug
        
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

# --- ROTA PARA O PROFESSOR VER SEUS ALUNOS (AGORA AGRUPADOS POR TURMA) ---
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
        # Busca todos os alunos vinculados, ordenando por turma e depois por nome
        comando = """
            SELECT idAluno, nomeAluno, emailAluno, status, moedas, nivel, anoAluno 
            FROM Aluno 
            WHERE idProfessor = %s 
            ORDER BY anoAluno, nomeAluno
        """
        cursor.execute(comando, (professor_id,))
        alunos = cursor.fetchall()
        
        # --- LÓGICA DE AGRUPAMENTO ---
        turmas = {}
        for aluno in alunos:
            # Usa 'Sem Turma' como padrão se o campo for nulo ou vazio
            turma_nome = aluno.get('anoaluno') or 'Alunos Sem Turma' 
            
            # Se a turma ainda não existe no nosso dicionário, cria a chave com uma lista vazia
            if turma_nome not in turmas:
                turmas[turma_nome] = []
            
            # Adiciona o aluno à lista da sua respectiva turma
            turmas[turma_nome].append(aluno)
            
        # O resultado final será um objeto, ex: {"1º Ano A": [...alunos], "2º Ano B": [...alunos]}
        return jsonify(turmas), 200

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

    professor_id = get_jwt_identity()

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
        
        # Converte o conteúdo para JSON string se for dicionário
        if isinstance(conteudo, dict):
            conteudo_json = _json.dumps(conteudo)
        else:
            conteudo_json = str(conteudo)
            
        # Converte turmas para JSON string se for lista
        if isinstance(turmas, list):
            turmas_json = _json.dumps(turmas)
        else:
            turmas_json = '[]'

        comando = '''
            INSERT INTO Atividade (titulo, tipo, descricao, conteudo_json, icon, idProfessor, status, turmas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING idAtividade
        '''
        cursor.execute(comando, (
            titulo, tipo, descricao, conteudo_json, icon, professor_id, 'available', turmas_json
        ))
        novo_id = cursor.fetchone()['idatividade']
        conexao.commit()
        
        return jsonify({
            "msg": "Atividade criada com sucesso!", 
            "idAtividade": novo_id
        }), 201

    except Exception as e:
        if conexao:
            conexao.rollback()
        print("Erro ao criar atividade:", e)
        return jsonify({"msg": f"Erro interno ao criar atividade: {str(e)}"}), 500
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



# --- NOVA ROTA PARA BUSCAR ALUNOS POR NOME ---
@app.route('/api/professor/alunos/buscar', methods=['GET'])
@jwt_required()
def buscar_alunos_por_nome():
    claims = get_jwt()
    if claims.get('role') != 'professor':
        return jsonify({"msg": "Acesso negado. Apenas para professores."}), 403
    
    professor_id = get_jwt_identity()
    
    # Pega o termo de busca dos parâmetros da URL (ex: /buscar?nome=João)
    termo_busca = request.args.get('nome', '').strip()

    # Validação para não buscar com menos de 2 caracteres
    if len(termo_busca) < 2:
        return jsonify([]) # Retorna uma lista vazia se a busca for muito curta

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        
        # O operador ILIKE é case-insensitive (não diferencia maiúsculas/minúsculas)
        # Os '%' são curingas: buscam qualquer coisa antes e depois do termo
        query = """
            SELECT idAluno, nomeAluno, emailAluno, status, moedas, nivel, anoAluno 
            FROM Aluno 
            WHERE idProfessor = %s AND nomeAluno ILIKE %s
            ORDER BY nomeAluno
        """
        # Formata o termo de busca para a query SQL
        termo_formatado = f"%{termo_busca}%"
        
        cursor.execute(query, (professor_id, termo_formatado))
        alunos_encontrados = cursor.fetchall()
        
        return jsonify(alunos_encontrados), 200

    except psycopg2.Error as e:
        print(f"Erro ao buscar alunos: {e}")
        return jsonify({"msg": "Erro interno ao realizar a busca."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

# --- ROTA PARA OBTER DADOS DO PERFIL DO PROFESSOR LOGADO ---
@app.route('/api/professor/perfil', methods=['GET'])
@jwt_required()
def get_professor_perfil():
    claims = get_jwt()
    if claims.get('role') != 'professor':
        return jsonify({"msg": "Acesso negado. Apenas para professores."}), 403
    
    professor_id = get_jwt_identity()

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        # Busca os dados do professor
        cursor.execute('SELECT nomeProfessor, emailProfessor, urlFotoPerfil FROM Professor WHERE idProfessor = %s', (professor_id,))
        professor_data = cursor.fetchone()

        if not professor_data:
            return jsonify({"msg": "Professor não encontrado."}), 404
        
        # Busca as turmas distintas que este professor leciona
        cursor.execute("SELECT DISTINCT anoAluno FROM Aluno WHERE idProfessor = %s ORDER BY anoAluno", (professor_id,))
        turmas_raw = cursor.fetchall()
        # Converte a lista de dicionários para uma lista de strings
        professor_data['turmas'] = [turma['anoaluno'] for turma in turmas_raw if turma['anoaluno']]

        return jsonify(professor_data), 200

    except psycopg2.Error as e:
        print(f"Erro de Banco de Dados no perfil do professor: {e}")
        return jsonify({"msg": "Erro interno no servidor."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

# --- ROTA PARA ATUALIZAR DADOS DO PERFIL DO PROFESSOR ---
@app.route('/api/professor/perfil', methods=['PUT'])
@jwt_required()
def update_professor_perfil():
    claims = get_jwt()
    if claims.get('role') != 'professor':
        return jsonify({"msg": "Acesso negado."}), 403
    
    professor_id = get_jwt_identity()
    data = request.get_json()
    novo_nome = data.get('nome')
    # Poderíamos adicionar outros campos como 'materias' aqui se tivéssemos uma coluna no DB

    if not novo_nome:
        return jsonify({"msg": "O nome não pode ser vazio."}), 400

    conexao = None
    cursor = None
    try:
        conexao, cursor = conectar_db()
        cursor.execute('UPDATE Professor SET nomeProfessor = %s WHERE idProfessor = %s', (novo_nome, professor_id))
        conexao.commit()
        
        # Atualiza o nome no localStorage do frontend
        return jsonify({"msg": "Perfil atualizado com sucesso!", "novoNome": novo_nome}), 200

    except psycopg2.Error as e:
        if conexao: conexao.rollback()
        print(f"Erro ao atualizar perfil do professor: {e}")
        return jsonify({"msg": "Erro interno ao atualizar perfil."}), 500
    finally:
        if cursor and conexao:
            encerrar_db(cursor, conexao)

if __name__ == '__main__':
    # Render usa um servidor WSGI (como Gunicorn), mas isso é bom para testes locais.
    # O Render ignora isso e usa o comando do seu "Build Command".
    app.run(debug=True, port=5000)