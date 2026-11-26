-- Dados iniciais de TESTE. Gerado por scripts/gerar_sql.py.
USE controle_atendimento;

INSERT INTO usuarios (nome, login, senha_hash, perfil, ativo) VALUES ('Gestor de Teste', 'gestor', '$2b$12$Wkf/yzcuJdxugSrhNwAHIO4WLORMXlJ6uB0kjiTMPTYqFQN0hoV4W', 'GESTOR', 1);  -- senha: gestor123
INSERT INTO usuarios (nome, login, senha_hash, perfil, ativo) VALUES ('Atendente Um', 'atendente1', '$2b$12$NlJIKDPHGbIXes7Trv328eBRqxrK4HEvLl4IX7Q5Bs18zZYDJLZAO', 'ATENDENTE', 1);  -- senha: atendente123
INSERT INTO usuarios (nome, login, senha_hash, perfil, ativo) VALUES ('Atendente Dois', 'atendente2', '$2b$12$PL/XGkGGWOUgnzWnxjsgYefi4lgzfcU7TIAqFhR6778bR23Ip.ZLS', 'ATENDENTE', 1);  -- senha: atendente123
INSERT INTO usuarios (nome, login, senha_hash, perfil, ativo) VALUES ('Atendente Tres', 'atendente3', '$2b$12$oJ3anrM4HdnrJRudO8BKyunXThqPNpEuZzcgiVbdkLhW1DGjKAnP2', 'ATENDENTE', 1);  -- senha: atendente123

INSERT INTO guiches (id, numero, ativo) VALUES (1, 1, 1);
INSERT INTO guiches (id, numero, ativo) VALUES (2, 2, 1);
INSERT INTO guiches (id, numero, ativo) VALUES (3, 3, 1);
INSERT INTO guiches (id, numero, ativo) VALUES (4, 4, 1);
INSERT INTO guiches (id, numero, ativo) VALUES (5, 5, 1);

INSERT INTO controle_fila (id) VALUES (1);
