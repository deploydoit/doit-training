# -*- coding: utf-8 -*-
"""Atualiza módulo Agenda: apagar evento, remove lançar horas, adiciona novas etapas."""
import sys
sys.path.insert(0, '.')

from uuid import uuid4
from models.database import Database


def main():
    db = Database("training.db")
    db.initialize()

    # 1. Atualizar 'Apagar evento' (pos4)
    content_apagar = (
        "# Apagar evento\n\n"
        "1. Acesse **Agenda \u2192 Lista**\n"
        "2. Encontre o evento\n"
        "3. Clique na lixeirinha ao final da barra\n\n"
        "Outra forma: toque no evento para abri-lo. Rolando para baixo na ficha, "
        "voc\u00ea encontra o \u00edcone da lixeira.\n\n"
        "*Aten\u00e7\u00e3o: a exclus\u00e3o \u00e9 permanente!*\n"
    )
    db.execute(
        "UPDATE step_contents SET content_data=? WHERE id=?",
        (content_apagar, "9d3d57a0-485b-4d74-8516-f644a248fba5"),
    )

    # 2. Remover 'Lançar horas' (pos5)
    step_lancar = "714b9e40-a1b3-423a-9435-b00298caf3aa"
    db.execute("PRAGMA foreign_keys = OFF")
    db.execute("DELETE FROM step_contents WHERE step_id=?", (step_lancar,))
    db.execute("DELETE FROM steps WHERE id=?", (step_lancar,))
    db.execute("PRAGMA foreign_keys = ON")

    # 3. Obter path_id
    row = db.execute("SELECT path_id FROM steps WHERE module_id='agenda' LIMIT 1").fetchone()
    pid = row["path_id"]

    # 4. Adicionar novas etapas
    novas = [
        (5, "# Setup\n\n"
            "Em **Agenda \u2192 Setup** (dispon\u00edvel para quem tiver acesso), \u00e9 poss\u00edvel:\n"
            "- Criar novas agendas p\u00fablicas\n"
            "- Editar nomes e cores das agendas existentes\n"
            "- Remover agendas que n\u00e3o s\u00e3o mais utilizadas\n\n"
            "Cada escrit\u00f3rio personaliza suas agendas p\u00fablicas conforme a rotina da equipe.\n"),
        (6, "# Lista\n\n"
            "Em **Agenda \u2192 Lista** voc\u00ea tem uma vis\u00e3o em formato de tabela com todos os eventos.\n\n"
            "\u00datil para:\n"
            "- Buscar eventos por data, nome ou projeto\n"
            "- Aplicar filtros para encontrar rapidamente o que procura\n"
            "- Ter uma vis\u00e3o geral sem depender do calend\u00e1rio visual\n"),
        (7, "# Recados\n\n"
            "Em **Agenda \u2192 Recados** voc\u00ea acessa o sistema de lembretes internos.\n\n"
            "- Envie recados r\u00e1pidos para outros colaboradores\n"
            "- O destinat\u00e1rio recebe uma notifica\u00e7\u00e3o\n"
            "- Comunica\u00e7\u00e3o unidirecional (n\u00e3o \u00e9 um chat \u2014 n\u00e3o permite resposta)\n\n"
            "\u00datil para avisos de prazos, lembretes operacionais e solicita\u00e7\u00f5es r\u00e1pidas.\n"),
        (8, "# Agendas Google\n\n"
            "Nesta se\u00e7\u00e3o voc\u00ea aprender\u00e1 a configurar a integra\u00e7\u00e3o entre a agenda do DOit e o Google Agenda.\n\n"
            "*Conte\u00fado em constru\u00e7\u00e3o \u2014 ser\u00e1 adicionado em breve.*\n"),
    ]

    for pos, text in novas:
        sid = str(uuid4())
        cid = str(uuid4())
        db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type) VALUES (?, ?, ?, ?, 'content')",
            (sid, "agenda", pid, pos),
        )
        db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) VALUES (?, ?, 'text', ?, 0)",
            (cid, sid, text),
        )

    db.commit()
    db.close()
    print("Agenda reorganizada: apagar evento atualizado, lançar horas removido, 4 novas etapas adicionadas.")


if __name__ == "__main__":
    main()
