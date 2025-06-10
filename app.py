from flask import Flask, request, jsonify
from flask_cors import CORS
from config import *
from db_functions import conectar_db, encerrar_db, limpar_input
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    senha = data.get('senha')

    if not email or not senha:
        return jsonify({'error': 'Campos obrigatórios'}), 400

    if email == MASTER_EMAIL and senha == MASTER_PASSWORD:
        return jsonify({'tipo': 'adm'}), 200

    try:
        conexao, cursor = conectar_db()

        cursor.execute("SELECT * FROM Aluno WHERE email = %s AND senha = %s", (email, senha))
        aluno = cursor.fetchone()
        if aluno:
            if aluno['status'] == 'inativo':
                return jsonify({'error': 'Aluno inativo'}), 403
            return jsonify({'tipo': 'aluno', 'id': aluno['idAluno'], 'nome': aluno['nomeAluno']}), 200

        cursor.execute("SELECT * FROM Professores WHERE email = %s AND senha = %s", (email, senha))
        professor = cursor.fetchone()
        if professor:
            return jsonify({'tipo': 'professor', 'id': professor['idProfessor'], 'nome': professor['nomeProfessor']}), 200

        return jsonify({'error': 'Credenciais inválidas'}), 401

    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        encerrar_db(cursor, conexao)


@app.route('/api/aluno', methods=['POST'])
def cadastrar_aluno():
    data = request.get_json()
    nome = data.get('nomeAluno')
    cpf = limpar_input(data.get('cpfAluno'))
    email = data.get('emailAluno')
    senha = data.get('senhaAluno')

    if not nome or not cpf or not email or not senha:
        return jsonify({'error': 'Todos os campos são obrigatórios'}), 400

    try:
        conexao, cursor = conectar_db()
        cursor.execute("INSERT INTO Aluno (nomeAluno, cpfAluno, email, senha) VALUES (%s, %s, %s, %s)",
                       (nome, cpf, email, senha))
        conexao.commit()
        return jsonify({'mensagem': 'Aluno cadastrado com sucesso'}), 201
    except Error as e:
        if e.errno == 1062:
            return jsonify({'error': 'Email já cadastrado'}), 409
        return jsonify({'error': str(e)}), 500
    finally:
        encerrar_db(cursor, conexao)


@app.route('/api/aluno/<int:idAluno>', methods=['PUT'])
def editar_aluno(idAluno):
    data = request.get_json()
    nome = data.get('nomeAluno')
    cpf = limpar_input(data.get('cpfAluno'))
    email = data.get('emailAluno')
    senha = data.get('senhaAluno')

    if not nome or not cpf or not email or not senha:
        return jsonify({'error': 'Todos os campos são obrigatórios'}), 400

    try:
        conexao, cursor = conectar_db()
        cursor.execute("""
            UPDATE Aluno
            SET nomeAluno = %s, cpfAluno = %s, email = %s, senha = %s
            WHERE idAluno = %s
        """, (nome, cpf, email, senha, idAluno))
        conexao.commit()
        return jsonify({'mensagem': 'Aluno atualizado com sucesso'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        encerrar_db(cursor, conexao)


@app.route('/api/alunos', methods=['GET'])
def listar_alunos():
    try:
        conexao, cursor = conectar_db()
        cursor.execute("SELECT * FROM Aluno")
        alunos = cursor.fetchall()
        return jsonify({'alunos': alunos}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        encerrar_db(cursor, conexao)

@app.route('/api/professor', methods=['POST'])
def cadastrar_professor():
    data = request.get_json()
    nome = data.get('nomeProfessor')
    cpf = limpar_input(data.get('cpfProfessor'))
    email = data.get('emailProfessor')
    senha = data.get('senhaProfessor')

    if not nome or not cpf or not email or not senha:
        return jsonify({'msg': 'Todos os campos são obrigatórios'}), 400

    try:
        conexao, cursor = conectar_db()
        cursor.execute("""
            INSERT INTO Professor (nomeProfessor, cpfProfessor, emailProfessor, senhaProfessor)
            VALUES (%s, %s, %s, %s)
        """, (nome, cpf, email, senha))
        conexao.commit()
        return jsonify({'msg': 'Professor cadastrado com sucesso!'}), 201
    except Error as e:
        if e.errno == 1062:
            return jsonify({'msg': 'E-mail ou CPF já cadastrado!'}), 409
        return jsonify({'msg': str(e)}), 500
    finally:
        encerrar_db(cursor, conexao)



@app.route('/api/resposta', methods=['POST'])
def salvar_resposta():
    data = request.get_json()
    aluno_id = data.get('aluno_id')
    atividade_id = data.get('atividade_id')
    resposta = data.get('resposta')

    if not aluno_id or not atividade_id or not resposta:
        return jsonify({'error': 'Campos obrigatórios'}), 400

    try:
        conexao, cursor = conectar_db()
        cursor.execute("INSERT INTO Respostas (aluno_id, atividade_id, resposta) VALUES (%s, %s, %s)",
                       (aluno_id, atividade_id, resposta))
        conexao.commit()
        return jsonify({'mensagem': 'Resposta salva com sucesso'}), 201
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        encerrar_db(cursor, conexao)


if __name__ == '__main__':
    app.run(debug=True)
