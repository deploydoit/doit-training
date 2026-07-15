# -*- coding: utf-8 -*-
"""Atualiza a etapa Integração com Google Agenda com conteúdo correto."""
import sys
sys.path.insert(0, '.')
import sqlite3
import base64

conn = sqlite3.connect('training.db')
conn.row_factory = sqlite3.Row

# Carregar ícone star
with open('media/agenda/star.png', 'rb') as f:
    b64_star = base64.b64encode(f.read()).decode()
star = f'<img src="data:image/png;base64,{b64_star}" style="width:16px;height:16px;vertical-align:middle;display:inline-block;">'

r = conn.execute("""SELECT sc.id FROM step_contents sc JOIN steps s ON sc.step_id=s.id
    WHERE s.module_id='agenda' AND s.position=5 AND sc.content_type='text'""").fetchone()

content = f"""## Integração com Google Agenda

### Agenda Pessoal — Assinar agenda externa

1. Acesse o menu superior direito do sistema
2. Clique em **Pref. Pessoais \u2192 Agenda \u2192 Externas**
3. Clique em {star}
4. Cole o link da sua agenda no campo correspondente (veja abaixo como obter)
5. Dê um nome para essa agenda (ex: "Agenda Google Pessoal") e escolha a cor

**Onde encontrar o link no Google Agenda:**

1. Acesse sua conta no Google Agenda
2. No menu lateral esquerdo, passe o mouse sobre a agenda desejada e clique nos três pontinhos (\u22ee)
3. Clique em **"Configurações e compartilhamento"**
4. Role até a seção **"Integrar agenda"**
5. Copie o link: **"Endereço secreto no formato iCal"** (termina com .ics)
6. Volte ao DOit e cole esse link na área de agendas externas

*Importante: é necessário pegar o link secreto no formato iCal, e não o link público.*

---

### Agenda Pública — Assinar agenda externa

Somente usuários com acesso ao Setup conseguem fazer essa configuração.

1. Acesse **Agenda \u2192 Setup \u2192 Externas**
2. Clique em {star}
3. Insira o link da agenda externa (mesmo processo acima para obter)
4. Dê um nome descritivo (ex: "Eventos Google da Equipe")
5. Ela será exibida na aba Pública da agenda de todos os usuários

*Atenção: essa agenda ficará visível a todos os usuários com acesso à agenda pública.*

---

### Compartilhar do DOit para o Google

1. No DOit, localize a agenda que deseja compartilhar
2. Toque no ícone do calendário
3. Copie o endereço do link gerado
4. No Google Agenda, clique em **"Adicionar outras agendas" \u2192 "Por URL"**
5. Cole o link copiado do DOit
6. Clique em **"Adicionar agenda"**

---

*Observações:*
- *O DOit só faz leitura da agenda externa. Ele não edita nem envia eventos de volta para a agenda original.*
- *A atualização pode levar alguns minutos, pois depende do serviço externo.*
- *É possível adicionar quantas agendas externas quiser.*
"""

conn.execute("UPDATE step_contents SET content_data=? WHERE id=?", (content, r['id']))
conn.commit()
print("Integração com Google Agenda atualizada corretamente")
conn.close()
