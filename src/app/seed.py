"""Dados iniciais (seed): usuários de teste, guichês e a linha de controle da fila.

Uso direto (cria as tabelas, se faltarem, e insere os dados):
    python -m app.seed          (rodar de dentro da pasta src)

Com Docker, não precisa: o MySQL já roda database/schema.sql e database/seed.sql.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.seguranca import gerar_hash
from app.models import ControleFila, Guiche, Perfil, Usuario

# Usuários de TESTE (documentados no README). Em produção, o gestor troca as senhas.
USUARIOS_TESTE = [
    {"nome": "Gestor de Teste", "login": "gestor", "senha": "gestor123", "perfil": Perfil.GESTOR},
    {"nome": "Atendente Um", "login": "atendente1", "senha": "atendente123", "perfil": Perfil.ATENDENTE},
    {"nome": "Atendente Dois", "login": "atendente2", "senha": "atendente123", "perfil": Perfil.ATENDENTE},
    {"nome": "Atendente Tres", "login": "atendente3", "senha": "atendente123", "perfil": Perfil.ATENDENTE},
]
QUANTIDADE_GUICHES = 5


def popular(db: Session) -> None:
    if db.scalar(select(Usuario).limit(1)) is not None:
        print("Banco já tem dados; seed ignorado.")
        return
    for u in USUARIOS_TESTE:
        db.add(Usuario(
            nome=u["nome"],
            login=u["login"],
            senha_hash=gerar_hash(u["senha"]),
            perfil=u["perfil"],
            ativo=True,
        ))
    for numero in range(1, QUANTIDADE_GUICHES + 1):
        db.add(Guiche(id=numero, numero=numero, ativo=True))
    db.add(ControleFila(id=1))
    db.commit()


if __name__ == "__main__":
    from app.database import Base, SessionLocal, engine

    Base.metadata.create_all(engine)
    with SessionLocal() as sessao:
        popular(sessao)
    print("Seed concluído.")
