# -*- coding: utf-8 -*-
"""Distribui as dicas do módulo 'boas-praticas' nos módulos temáticos corretos.

- Projetos: criar, equipe, pedidos, despesa, ata, editar TA/RT, ocultar status
- Financeiro: cobranças (HTs, TAs, ETs, RDs), relatórios, NFs
- Agenda: eventos, horas, sincronização
- E-mail: modelos, listas, senha

Depois remove o módulo 'boas-praticas'.
"""

import sys
sys.path.insert(0, '.')

from uuid import uuid4
from models.database import Database


# Mapa: posição no boas-praticas -> módulo destino
# (posições 0 e 25 são intro/conclusão, serão descartadas)
POSITION_TO_MODULE = {
    1: "projetos",    # Como criar um Projeto
    2: "projetos",    # Designar Líder
    3: "projetos",    # Equipe Padrão
    4: "projetos",    # Equipe Interna
    5: "projetos",    # Criar Pedidos
    6: "financeiro",  # Cobrar HTs
    7: "financeiro",  # Cobrar TAs
    8: "financeiro",  # Cobrar ETs
    9: "financeiro",  # Cobrar RDs
    10: "projetos",   # Registrar despesa reembolso
    11: "projetos",   # Ata de Reunião
    12: "projetos",   # Editar TA/RT
    13: "projetos",   # Ocultar Status
    14: "agenda",     # Criar evento pessoal
    15: "agenda",     # Criar evento público
    16: "agenda",     # Apagar evento
    17: "agenda",     # Lançar horas
    18: "agenda",     # Sincronizar iPhone
    19: "email",      # Criar modelos
    20: "email",      # Criar lista
    21: "email",      # Atualizar senha
    22: "financeiro", # Relatório multi-conta
    23: "financeiro", # NF de Serviço
    24: "financeiro", # NF avulsa
}


def _get_main_path(db, module_id):
    """Retorna o path principal de um módulo."""
    row = db.execute(
        "SELECT id FROM paths WHERE module_id = ? AND is_main = 1", (module_id,)
    ).fetchone()
    if row is None:
        # fallback: qualquer path do módulo
        row = db.execute(
            "SELECT id FROM paths WHERE module_id = ? LIMIT 1", (module_id,)
        ).fetchone()
    return row["id"] if row else None


def _next_position(db, module_id, path_id):
    """Retorna a próxima posição disponível no path."""
    row = db.execute(
        "SELECT MAX(position) as mp FROM steps WHERE module_id = ? AND path_id = ?",
        (module_id, path_id),
    ).fetchone()
    mp = row["mp"]
    return (mp + 1) if mp is not None else 0


def _clean_title_prefix(text):
    """Remove prefixos redundantes como 'Agenda — ', 'E-mail — ', 'Financeiro — '.

    Como as dicas vão para o módulo temático, o prefixo é desnecessário.
    """
    replacements = [
        ("## Agenda — Criar evento pessoal", "## Criar evento pessoal"),
        ("## Agenda — Criar evento em agenda pública", "## Criar evento em agenda pública"),
        ("## Agenda — Apagar evento", "## Apagar evento"),
        ("## Agenda — Lançar horas a partir de evento", "## Lançar horas a partir de evento"),
        ("## Agenda — Sincronizar com iPhone", "## Sincronizar com iPhone"),
        ("## E-mail — Criar modelos", "## Criar modelos de e-mail"),
        ("## E-mail — Criar lista de e-mail", "## Criar lista de e-mail"),
        ("## E-mail — Atualizar senha", "## Atualizar senha de e-mail"),
        ("## Financeiro — Relatório com múltiplas contas", "## Relatório com múltiplas contas"),
        ("## Financeiro — Emitir NF de Serviço", "## Emitir NF de Serviço"),
        ("## Financeiro — Emitir NF avulsa", "## Emitir NF avulsa"),
    ]
    for old, new in replacements:
        if text.strip().startswith(old):
            return text.replace(old, new, 1)
    return text


def migrate(db):
    """Executa a migração das dicas."""

    # Buscar todas as etapas do boas-praticas com conteúdo
    steps = db.execute("""
        SELECT s.position, s.id as step_id, sc.id as content_id, sc.content_data
        FROM steps s
        JOIN step_contents sc ON sc.step_id = s.id
        WHERE s.module_id = 'boas-praticas'
        ORDER BY s.position
    """).fetchall()

    moved = {"projetos": 0, "financeiro": 0, "agenda": 0, "email": 0}

    for step in steps:
        pos = step["position"]
        target = POSITION_TO_MODULE.get(pos)
        if target is None:
            continue  # intro/conclusão, descartar

        path_id = _get_main_path(db, target)
        if path_id is None:
            print(f"  AVISO: módulo '{target}' sem path. Pulando posição {pos}.")
            continue

        new_pos = _next_position(db, target, path_id)
        content = _clean_title_prefix(step["content_data"])

        # Criar nova etapa no módulo destino
        new_step_id = str(uuid4())
        new_content_id = str(uuid4())
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) "
            "VALUES (?, ?, ?, ?, 'content')",
            (new_step_id, target, path_id, new_pos),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
            "VALUES (?, ?, 'text', ?, 0)",
            (new_content_id, new_step_id, content),
        )
        moved[target] += 1

    db.commit()

    print("Dicas migradas:")
    for mod, count in moved.items():
        print(f"  {mod:12} +{count} etapas")

    # Remover o módulo boas-praticas por completo
    db.execute("PRAGMA foreign_keys = OFF")
    db.execute("DELETE FROM step_contents WHERE step_id IN (SELECT id FROM steps WHERE module_id = 'boas-praticas')")
    db.execute("DELETE FROM steps WHERE module_id = 'boas-praticas'")
    db.execute("DELETE FROM paths WHERE module_id = 'boas-praticas'")
    db.execute("DELETE FROM modules WHERE id = 'boas-praticas'")
    db.commit()
    print("\nMódulo 'boas-praticas' removido.")


def main():
    db = Database("training.db")
    db.initialize()
    print("Redistribuindo dicas nos módulos temáticos...\n")
    migrate(db)
    db.close()
    print("\nConcluído! Reinicie o app para ver as mudanças.")


if __name__ == "__main__":
    main()
