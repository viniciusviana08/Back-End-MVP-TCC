-- Script para PostgreSQL

CREATE TABLE Professor (
    idProfessor SERIAL PRIMARY KEY,
    nomeProfessor VARCHAR(100) NOT NULL,
    cpfProfessor VARCHAR(11) NOT NULL UNIQUE,
    emailProfessor VARCHAR(100) NOT NULL UNIQUE,
    senhaProfessor VARCHAR(255) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'inativo'))
);

CREATE TABLE Aluno (
    idAluno SERIAL PRIMARY KEY,
    nomeAluno VARCHAR(100) NOT NULL,
    cpfAluno VARCHAR(11) NOT NULL UNIQUE,
    emailAluno VARCHAR(100) NOT NULL UNIQUE,
    senhaAluno VARCHAR(255) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'inativo')),
    moedas INT NOT NULL DEFAULT 100,
    nivel VARCHAR(50) NOT NULL DEFAULT 'Iniciante 1'
);

CREATE TABLE Atividade (
    idAtividade SERIAL PRIMARY KEY,
    idProfessor INT NOT NULL,
    nomeAtividade VARCHAR(100) NOT NULL,
    tipoAtividade VARCHAR(20) NOT NULL CHECK (tipoAtividade IN ('correcao_texto', 'multipla_escolha', 'acentuacao')),
    dificuldade VARCHAR(10) NOT NULL CHECK (dificuldade IN ('facil', 'medio', 'dificil')),
    descricaoAtividade TEXT,
    FOREIGN KEY (idProfessor) REFERENCES Professor(idProfessor)
);

CREATE TABLE AtividadeFeita (
    idAtividadeFeita SERIAL PRIMARY KEY,
    idAluno INT NOT NULL,
    idAtividade INT NOT NULL,
    dataAtividadeFeita TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (idAluno) REFERENCES Aluno(idAluno),
    FOREIGN KEY (idAtividade) REFERENCES Atividade(idAtividade)
);