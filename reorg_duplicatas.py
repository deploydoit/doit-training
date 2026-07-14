# -*- coding: utf-8 -*-
"""Remove duplicatas e reordena as etapas dos módulos Projetos e Agenda.

Projetos: mescla visões gerais (ricas) com as dicas novas, removendo
os passos concisos que apenas repetem o que a visão geral já cobre.

Agenda: idem.
"""

import sys
sys.path.insert(0, '.')

from models.database import Database


def _title(text):
    """Extrai o título (primeira linha) do conteúdo."""
    return text.strip().split("\n")[0].replace("#", "").strip()


def _get_steps(db, module_id):
    """Retorna lista de (step_id, position, content_id, title, content)."""
    rows = db.execute("""
        SELECT s.id as step_id, s.position, s.path_id,
               sc.id as content_id, sc.content_data
        FROM steps s JOIN step_contents sc ON sc.step_id = s.id
        WHERE s.module_id = ? ORDER BY s.position
    """, (module_id,)).fetchall()
    return [
        {
            "step_id": r["step_id"],
            "position": r["position"],
            "path_id": r["path_id"],
            "content_id": r["content_id"],
            "content": r["content_data"],
            "title": _title(r["content_data"]),
        }
        for r in rows
    ]


def _delete_step(db, step_id):
    db.execute("DELETE FROM step_contents WHERE step_id = ?", (step_id,))
    db.execute("DELETE FROM steps WHERE id = ?", (step_id,))


def _reorder(db, module_id, ordered_titles):
    """Reordena as etapas de um módulo conforme a lista de títulos.

    Etapas cujos títulos não estão na lista são deletadas.
    """
    steps = _get_steps(db, module_id)
    by_title = {s["title"]: s for s in steps}

    # Deletar etapas que não estão na ordem desejada
    keep_titles = set(ordered_titles)
    for s in steps:
        if s["title"] not in keep_titles:
            _delete_step(db, s["step_id"])
            print(f"  [{module_id}] removida: {s['title']}")

    # Mover todas as posições para faixa alta temporária (evita colisão)
    remaining = _get_steps(db, module_id)
    for i, s in enumerate(remaining):
        db.execute(
            "UPDATE steps SET position = ? WHERE id = ?",
            (1000 + i, s["step_id"]),
        )
    db.commit()

    # Aplicar posições finais na ordem desejada
    pos = 0
    for title in ordered_titles:
        s = by_title.get(title)
        if s is None:
            print(f"  [{module_id}] AVISO: título não encontrado: {title}")
            continue
        db.execute(
            "UPDATE steps SET position = ? WHERE id = ?",
            (pos, s["step_id"]),
        )
        pos += 1
    db.commit()
    print(f"  [{module_id}] reordenado: {pos} etapas.")


def reorg_projetos(db):
    """Reorganiza o módulo Projetos."""
    # Ordem final desejada (títulos exatos das etapas a manter)
    ordered = [
        "Módulo: Projetos",
        "Criar um Projeto",
        "Como designar o Líder do Projeto",
        "Equipe Interna e Setup",
        "Equipe Padrão — adicionar membro",
        "Lançar Horas e Despesas",
        "Como registrar despesa para reembolso",
        "Como criar Pedidos",
        "Como editar TA/RT já calculada",
        "Atas de Reunião",
        "Como ocultar Status de projetos",
    ]
    # Títulos removidos (duplicatas): "Como criar um Projeto",
    # "Equipe Interna — adicionar membro a um projeto", "Como criar Ata de Reunião"
    _reorder(db, "projetos", ordered)


def reorg_agenda(db):
    """Reorganiza o módulo Agenda."""
    ordered = [
        "Módulo: Agenda",
        "Criar um Evento",
        "Salvar, Enviar e Compartilhar",
        "Criar evento em agenda pública",
        "Apagar evento",
        "Lançar horas a partir de evento",
        "Sincronizar com iPhone",
    ]
    # Removido (duplicata): "Criar evento pessoal"
    _reorder(db, "agenda", ordered)


def fix_premature_conclusion(db):
    """Remove a frase 'Módulo Projetos concluído!' do meio do módulo."""
    rows = db.execute(
        "SELECT id, content_data FROM step_contents WHERE content_data LIKE '%Módulo Projetos concluído%'"
    ).fetchall()
    for r in rows:
        new = r["content_data"].replace("\n\nMódulo Projetos concluído!", "")
        new = new.replace("Módulo Projetos concluído!", "")
        db.execute("UPDATE step_contents SET content_data = ? WHERE id = ?", (new.rstrip(), r["id"]))
    db.commit()
    if rows:
        print("  Conclusão prematura removida de Projetos.")


def main():
    db = Database("training.db")
    db.initialize()
    print("Reorganizando duplicatas...\n")
    fix_premature_conclusion(db)
    reorg_projetos(db)
    reorg_agenda(db)
    db.close()
    print("\nConcluído! Reinicie o app.")


if __name__ == "__main__":
    main()
