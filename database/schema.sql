-- Gerado por scripts/gerar_sql.py a partir de src/app/models.py. Não edite à mão.
CREATE DATABASE IF NOT EXISTS controle_atendimento CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE controle_atendimento;

CREATE TABLE controle_fila (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	ultimo_tipo_chamado VARCHAR(20), 
	data_referencia DATE, 
	atualizado_em DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_controle_tipo CHECK (ultimo_tipo_chamado IN ('SP', 'SG', 'SE'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE guiches (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	numero INTEGER NOT NULL, 
	ativo BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (numero)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE sequencias_diarias (
	data DATE NOT NULL, 
	tipo VARCHAR(20) NOT NULL, 
	ultimo_numero INTEGER NOT NULL, 
	PRIMARY KEY (data, tipo), 
	CONSTRAINT ck_seq_tipo CHECK (tipo IN ('SP', 'SG', 'SE'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE usuarios (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	nome VARCHAR(100) NOT NULL, 
	login VARCHAR(50) NOT NULL, 
	senha_hash VARCHAR(100) NOT NULL, 
	perfil VARCHAR(20) NOT NULL, 
	ativo BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (login), 
	CONSTRAINT ck_usuarios_perfil CHECK (perfil IN ('ATENDENTE', 'GESTOR'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE senhas (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	numero VARCHAR(12) NOT NULL, 
	tipo VARCHAR(20) NOT NULL, 
	sequencial INTEGER NOT NULL, 
	data_emissao DATE NOT NULL, 
	estado VARCHAR(20) NOT NULL, 
	emitida_em DATETIME NOT NULL, 
	primeira_chamada_em DATETIME, 
	segunda_chamada_em DATETIME, 
	inicio_atendimento_em DATETIME, 
	fim_atendimento_em DATETIME, 
	guiche_id INTEGER, 
	atendente_id INTEGER, 
	motivo_encerramento VARCHAR(40), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_senhas_dia_tipo_seq UNIQUE (data_emissao, tipo, sequencial), 
	UNIQUE (numero), 
	CONSTRAINT ck_senhas_tipo CHECK (tipo IN ('SP', 'SG', 'SE')), 
	CONSTRAINT ck_senhas_estado CHECK (estado IN ('EMITIDA', 'AGUARDANDO', 'CHAMADA', 'CHAMADA_NOVAMENTE', 'EM_ATENDIMENTO', 'ATENDIDA', 'NAO_COMPARECEU')), 
	FOREIGN KEY(guiche_id) REFERENCES guiches (id), 
	FOREIGN KEY(atendente_id) REFERENCES usuarios (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_senhas_fila ON senhas (data_emissao, estado, tipo, sequencial);
CREATE INDEX ix_senhas_guiche_estado ON senhas (guiche_id, estado);

CREATE TABLE historico_estados (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	senha_id INTEGER NOT NULL, 
	estado_anterior VARCHAR(20), 
	estado_novo VARCHAR(20) NOT NULL, 
	usuario_id INTEGER, 
	guiche_id INTEGER, 
	ocorrido_em DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(senha_id) REFERENCES senhas (id), 
	CONSTRAINT ck_hist_anterior CHECK (estado_anterior IN ('EMITIDA', 'AGUARDANDO', 'CHAMADA', 'CHAMADA_NOVAMENTE', 'EM_ATENDIMENTO', 'ATENDIDA', 'NAO_COMPARECEU')), 
	CONSTRAINT ck_hist_novo CHECK (estado_novo IN ('EMITIDA', 'AGUARDANDO', 'CHAMADA', 'CHAMADA_NOVAMENTE', 'EM_ATENDIMENTO', 'ATENDIDA', 'NAO_COMPARECEU')), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id), 
	FOREIGN KEY(guiche_id) REFERENCES guiches (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_hist_estado_data ON historico_estados (estado_novo, ocorrido_em);
CREATE INDEX ix_hist_senha ON historico_estados (senha_id);
