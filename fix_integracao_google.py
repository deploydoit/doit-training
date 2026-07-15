# -*- coding: utf-8 -*-
"""Atualiza a etapa Integração com Google Agenda."""
import sys
sys.path.insert(0, '.')
import sqlite3

conn = sqlite3.connect('training.db')
conn.row_factory = sqlite3.Row

r = conn.execute("""SELECT sc.id FROM step_contents sc JOIN steps s ON sc.step_id=s.id
    WHERE s.module_id='agenda' AND s.position=5 AND sc.content_type='text'""").fetchone()

content = """## Integração com Google Agenda

Existem duas formas de trazer uma agenda externa do Google para dentro do DOit:

**1. Assinar agenda externa na sua agenda pessoal:**

1. Acesse **Agenda → Pessoal**
2. Toque na engrenagem
3. Clique em **"Agendas Externas"**
4. No Google Agenda, copie o endereço público em formato iCal da agenda desejada
5. Cole a URL no DOit e salve

Os eventos do Google passarão a aparecer na sua agenda pessoal do DOit.

**2. Assinar agenda externa em uma agenda pública:**

1. Acesse **Agenda → Públicas**
2. Toque na engrenagem
3. Clique em **"Agendas Externas"**
4. No Google Agenda, copie o endereço público em formato iCal
5. Cole a URL no DOit e salve

Os eventos do Google aparecerão na agenda pública selecionada, visível para toda a equipe.

**Compartilhar do DOit para o Google:**

1. No DOit, localize a agenda que deseja compartilhar
2. Toque no ícone do calendário
3. Copie o endereço do link gerado
4. No Google Agenda, clique em **"Adicionar outras agendas" → "Por URL"**
5. Cole o link copiado do DOit
6. Clique em **"Adicionar agenda"**

Os eventos do DOit passarão a aparecer no seu Google Agenda.

---

*Observação: a sincronização pode levar alguns minutos para atualizar. Alterações feitas no Google não refletem no DOit automaticamente — a sincronização é de visualização.*
"""

conn.execute("UPDATE step_contents SET content_data=? WHERE id=?", (content, r['id']))
conn.commit()
print("Integração com Google Agenda atualizada")
conn.close()
