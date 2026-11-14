-- Schema do SQLite — tradução do db_init.sql (MySQL) original.
-- Diferenças de dialeto:
--   AUTO_INCREMENT  -> INTEGER PRIMARY KEY AUTOINCREMENT
--   ENUM(...)       -> TEXT + CHECK (o SQLite não tem ENUM)
--   LONGBLOB        -> BLOB
--   ENGINE/CHARSET  -> não existem no SQLite

CREATE TABLE IF NOT EXISTS tb_clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE,
    nascimento TEXT,
    cpf TEXT UNIQUE,
    rg TEXT UNIQUE,
    senha TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tb_empresa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cnpj TEXT NOT NULL UNIQUE,
    segmento TEXT NOT NULL CHECK (segmento IN ('Clinica particular', 'Clinica pública', 'Hospital')),
    funcionarios INTEGER DEFAULT NULL,
    site TEXT DEFAULT NULL,
    logo BLOB DEFAULT NULL,
    email TEXT NOT NULL,
    telefone TEXT NOT NULL,
    cep TEXT NOT NULL,
    endereco TEXT NOT NULL,
    cidade TEXT NOT NULL,
    estado TEXT NOT NULL,
    senha TEXT NOT NULL,
    confirmar_senha TEXT NOT NULL,
    descricao TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pacientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cpf TEXT,
    nome TEXT,
    nascimento TEXT,
    telefone TEXT,
    sintomas TEXT,
    classificacao TEXT CHECK (classificacao IN ('verde','amarelo','laranja','vermelho')),
    responsavel TEXT,
    empresa_id INTEGER,
    entrada_inicio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    entrada_fim TIMESTAMP NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES tb_empresa(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fila (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL,
    empresa_id INTEGER NOT NULL,
    chamado INTEGER DEFAULT 0,
    chegada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    FOREIGN KEY (empresa_id) REFERENCES tb_empresa(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS em_atendimento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER,
    empresa_id INTEGER,
    cpf TEXT,
    nome TEXT,
    nascimento TEXT,
    telefone TEXT,
    sintomas TEXT,
    classificacao TEXT CHECK (classificacao IN ('verde','amarelo','laranja','vermelho')),
    responsavel TEXT,
    inicio_atendimento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fim_atendimento TIMESTAMP NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE SET NULL,
    FOREIGN KEY (empresa_id) REFERENCES tb_empresa(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS profissionais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_empresa INTEGER NOT NULL,
    nome_completo TEXT NOT NULL,
    data_nascimento TEXT,
    telefone TEXT,
    email_profissional TEXT UNIQUE NOT NULL,
    especialidade TEXT NOT NULL,
    registro_crm_coren TEXT UNIQUE NOT NULL,
    estado_crm TEXT NOT NULL,
    turno_atendimento TEXT NOT NULL,
    status_clinica TEXT NOT NULL,
    informacoes_adicionais TEXT,
    FOREIGN KEY (id_empresa) REFERENCES tb_empresa(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pacientes_empresa_cpf ON pacientes(empresa_id, cpf);
CREATE INDEX IF NOT EXISTS idx_fila_empresa_chegada ON fila(empresa_id, chegada);
