# -*- coding: utf-8 -*-
"""Corrige etapa Recados: remove img inline e usa imagem separada com texto dividido."""
import sys
sys.path.insert(0, '.')
import sqlite3
from uuid import uuid4

conn = sqlite3.connect('training.db')
conn.row_factory = sqlite3.Row

step_id = 'b963b53d-a411-49d7-80cd-f29516c515b9'

# Remover todo o conteúdo existente desta etapa
conn.execute("DELETE FROM step_contents WHERE step_id=?", (step_id,))

# Texto principal (antes da imagem)
text1 = """## Recados

Sistema de lembretes internos entre usuários. Não é um chat.

**Como funciona:**
- Ao enviar, o destinatário recebe uma notificação
- Não é possível responder — comunicação unidirecional
- Use para avisos rápidos e lembretes

Quando você receber um recado, aparecerá o indicador abaixo com a quantidade de recados pendentes. Ele permanece visível até que você abra e leia os recados.
"""

# Texto após a imagem (observação/exemplos)
text2 = """*Exemplos: solicitação de retorno para fornecedor, avisos de prazos, lembretes operacionais.*
"""

# Inserir: texto1 (order 0), notificacaorecado (order 1), criarrecado (order 2), text2 (order 3)
conn.execute("""INSERT INTO step_contents (id, step_id, content_type, content_data, display_order)
    VALUES (?, ?, 'text', ?, 0)""", (str(uuid4()), step_id, text1))

conn.execute("""INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order)
    VALUES (?, ?, 'image', 'media/agenda/notificacaorecado.png', 'Indicador de recados pendentes', 1)""",
    (str(uuid4()), step_id))

conn.execute("""INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order)
    VALUES (?, ?, 'image', 'media/agenda/criarrecado.png', 'Criar um recado', 2)""",
    (str(uuid4()), step_id))

conn.execute("""INSERT INTO step_contents (id, step_id, content_type, content_data, display_order)
    VALUES (?, ?, 'text', ?, 3)""", (str(uuid4()), step_id, text2))

conn.commit()
print("Recados corrigido: sem img inline, imagem como registro separado")
conn.close()
