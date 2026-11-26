"""Gera database/schema.sql e database/seed.sql (MySQL 8) a partir dos modelos.

Por quê? Para o banco ter UMA fonte de verdade (src/app/models.py). Se alguém mudar
um modelo, roda este script de novo e os .sql ficam iguais ao código.

Uso (na raiz do projeto):
    python scripts/gerar_sql.py
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
# Só precisamos dos modelos; estas variáveis evitam exigir um .env para gerar o SQL
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "apenas-para-gerar-sql")

from sqlalchemy.dialects import mysql  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402

from app.core.seguranca import gerar_hash  # noqa: E402
from app.database import Base  # noqa: E402
import app.models  # noqa: E402,F401  (registra as tabelas no Base)
from app.seed import QUANTIDADE_GUICHES, USUARIOS_TESTE  # noqa: E402

dialeto = mysql.dialect()


def gerar_schema() -> str:
    partes = [
        "-- Gerado por scripts/gerar_sql.py a partir de src/app/models.py. Não edite à mão.",
        "CREATE DATABASE IF NOT EXISTS controle_atendimento CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;",
        "USE controle_atendimento;",
        "",
    ]
    for tabela in Base.metadata.sorted_tables:
        ddl = str(CreateTable(tabela).compile(dialect=dialeto)).strip()
        partes.append(f"{ddl} ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n")
        for indice in sorted(tabela.indexes, key=lambda i: i.name):
            partes.append(f"{str(CreateIndex(indice).compile(dialect=dialeto)).strip()};")
        partes.append("")
    return "\n".join(partes)


def gerar_seed() -> str:
    linhas = [
        "-- Dados iniciais de TESTE. Gerado por scripts/gerar_sql.py.",
        "USE controle_atendimento;",
        "",
    ]
    for u in USUARIOS_TESTE:
        linhas.append(
            "INSERT INTO usuarios (nome, login, senha_hash, perfil, ativo) VALUES "
            f"('{u['nome']}', '{u['login']}', '{gerar_hash(u['senha'])}', '{u['perfil'].value}', 1);"
            f"  -- senha: {u['senha']}"
        )
    linhas.append("")
    for n in range(1, QUANTIDADE_GUICHES + 1):
        linhas.append(f"INSERT INTO guiches (id, numero, ativo) VALUES ({n}, {n}, 1);")
    linhas += ["", "INSERT INTO controle_fila (id) VALUES (1);", ""]
    return "\n".join(linhas)


if __name__ == "__main__":
    (RAIZ / "database" / "schema.sql").write_text(gerar_schema(), encoding="utf-8")
    (RAIZ / "database" / "seed.sql").write_text(gerar_seed(), encoding="utf-8")
    print("Gerados: database/schema.sql e database/seed.sql")
