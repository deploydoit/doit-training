# -*- coding: utf-8 -*-
"""Insere as imagens novas nas etapas do módulo Agenda."""
import sys
sys.path.insert(0, '.')
import sqlite3
from uuid import uuid4

conn = sqlite3.connect('training.db')
conn.row_factory = sqlite3.Row

# Mapa: step_id -> lista de (imagem, alt_text, display_order)
images = [
    # pos1: Criar um Evento -> criarevento (já pode existir), salvar, salvareenviar, criarata, lancarhoras
    ("agenda_s1", "media/agenda/criarevento.png", "Tela de criar evento", 1),
    ("agenda_s1", "media/agenda/salvar.png", "Botão salvar", 2),
    ("agenda_s1", "media/agenda/salvareenviar.png", "Botão salvar e enviar convite", 3),
    ("agenda_s1", "media/agenda/criarata.png", "Criar ata de reunião", 4),
    ("agenda_s1", "media/agenda/lancarhoras.png", "Lançar horas a partir de evento", 5),

    # pos3: Compartilhar sua Agenda -> compartilhar
    ("agenda_s2", "media/agenda/compartilhar.png", "Tela de compartilhar agenda", 1),

    # pos6: Lista -> lista
    ("b1aa3ab6-74a4-4ae6-b0f7-cef3f6434ca4", "media/agenda/lista.png", "Aba Lista da agenda", 1),

    # pos7: Setup -> setup
    ("b60e847c-0e77-4aad-9578-a499bf69a0f7", "media/agenda/setup.png", "Tela de Setup da agenda", 1),

    # pos8: Recados -> criarrecado, notificacaorecado
    ("b963b53d-a411-49d7-80cd-f29516c515b9", "media/agenda/criarrecado.png", "Criar um recado", 1),
    ("b963b53d-a411-49d7-80cd-f29516c515b9", "media/agenda/notificacaorecado.png", "Notificação de recado", 2),
]

# Remover imagens anteriores dessas etapas (para não duplicar)
step_ids = set(i[0] for i in images)
for sid in step_ids:
    conn.execute("DELETE FROM step_contents WHERE step_id=? AND content_type='image'", (sid,))

# Inserir
for step_id, path, alt, order in images:
    cid = str(uuid4())
    conn.execute("""INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order)
        VALUES (?, ?, 'image', ?, ?, ?)""", (cid, step_id, path, alt, order))

conn.commit()
print(f"{len(images)} imagens inseridas nas etapas do módulo Agenda")
conn.close()
