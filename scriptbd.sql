CREATE DATABASE IF NOT EXISTS OrtoFix;
USE OrtoFix;

CREATE TABLE Professor (
    idProfessor INT PRIMARY KEY AUTO_INCREMENT,
    nomeProfessor VARCHAR(100) NOT NULL,
    cpfProfessor VARCHAR(11) NOT NULL UNIQUE,
    emailProfessor VARCHAR(100) NOT NULL UNIQUE,
    -- Aumentado para armazenar o hash da senha
    senhaProfessor VARCHAR(255) NOT NULL, 
    status ENUM('ativo', 'inativo') NOT NULL DEFAULT 'ativo'
) ENGINE=InnoDB; -- Removida a vírgula final

CREATE TABLE Aluno (
    idAluno INT PRIMARY KEY AUTO_INCREMENT,
    nomeAluno VARCHAR(100) NOT NULL,
    cpfAluno VARCHAR(11) NOT NULL UNIQUE,
    emailAluno VARCHAR(100) NOT NULL UNIQUE,
    -- Aumentado para armazenar o hash da senha
    senhaAluno VARCHAR(255) NOT NULL, 
    status ENUM('ativo', 'inativo') NOT NULL DEFAULT 'ativo',
    -- Colunas adicionadas para corresponder ao front-end
    moedas INT NOT NULL DEFAULT 100,
    nivel VARCHAR(50) NOT NULL DEFAULT 'Iniciante 1'
) ENGINE=InnoDB; -- Removida a vírgula final

CREATE TABLE Atividade (
    idAtividade INT PRIMARY KEY AUTO_INCREMENT,
    idProfessor INT NOT NULL,
    nomeAtividade VARCHAR(100) NOT NULL,
    -- Sugestão de ENUM mais descritivo
    tipoAtividade ENUM('correcao_texto', 'multipla_escolha', 'acentuacao') NOT NULL, 
    -- Sugestão de ENUM para dificuldade
    dificuldade ENUM('facil', 'medio', 'dificil') NOT NULL, 
    descricaoAtividade TEXT,
    FOREIGN KEY (idProfessor) REFERENCES Professor(idProfessor)
) ENGINE=InnoDB;

CREATE TABLE AtividadeFeita (
    idAtividadeFeita INT PRIMARY KEY AUTO_INCREMENT,
    idAluno INT NOT NULL,
    idAtividade INT NOT NULL,
    dataAtividadeFeita DATETIME DEFAULT CURRENT_TIMESTAMP,
    -- O idProfessor pode ser obtido via JOIN com a tabela Atividade, 
    -- então não é estritamente necessário aqui, mas pode manter se quiser.
    -- idProfessor INT NOT NULL, 
    FOREIGN KEY (idAluno) REFERENCES Aluno(idAluno),
    FOREIGN KEY (idAtividade) REFERENCES Atividade(idAtividade)
    -- FOREIGN KEY (idProfessor) REFERENCES Professor(idProfessor)
) ENGINE=InnoDB;

-- Exemplo de insert com senha (a senha real seria 'senha123')
-- O back-end irá gerar o hash antes de inserir.
-- INSERT INTO Aluno (nomeAluno, cpfAluno, emailAluno, senhaAluno, status)
-- VALUES
-- ('Pietro Santos', '47808481807', 'pietro.santos.senai@gmail.com', 'hash_da_senha_123', 'ativo');