# -*- coding: utf-8 -*-
"""Padroniza exemplos (itálico/cinza) e corrige acentuação em vários módulos."""

import sys
sys.path.insert(0, '.')

from models.database import Database


UPDATES = {
    # Recados: exemplo abaixo da imagem, em itálico
    "c_dashboard_s4": """# Recados

Sistema de lembretes internos entre usuários. Não é um chat.

- Ao enviar, o destinatário recebe uma notificação
- Não é possível responder — comunicação unidirecional
- Use para avisos rápidos e lembretes

---

*Exemplos: solicitação de retorno para fornecedor, avisos de prazos, lembretes operacionais.*
""",

    # E-mail: exemplo em itálico + correções de acento
    "c_email_s0": """# E-mail

O DOit registra todos os e-mails enviados pelo sistema.
Ele não recebe e-mails — funciona como ferramenta de envio e histórico.

---

**O que você encontra aqui**

| Aba | Conteúdo |
|---|---|
| Meus E-mails | E-mails enviados por você pelo DOit |
| Todos E-mails | E-mails de todos os usuários (requer permissão) |
| Ficha | Detalhes do e-mail selecionado |
| Modelos | Templates reutilizáveis para agilizar envios |
| Setup | Configuração de contas de envio |

---

**Modelos de E-mail**

Modelos são templates prontos para e-mails recorrentes.

*Exemplos de uso: propostas, contratos, cobranças de etapas, felicitações.*

- Meus Modelos — criados por você, privados por padrão
- Modelos Públicos — compartilhados com toda a equipe

Para criar: E-mail / Modelos / Meus Modelos / Novo
Para usar: clique no ícone de envio ao lado do modelo — um rascunho é criado com o conteúdo preenchido.

É possível proteger um modelo contra edições de outros usuários.
""",

    # Financeiro Recorrências: exemplo em itálico
    "c_financeiro_s1": """# Recorrências — Despesas Fixas

Para lançamentos que acontecem **todo mês** (evita criar manualmente).

*Exemplos: Salários, Aluguel, Energia, Internet, Telefonia, Contratos.*

**Criar:** Financeiro → Operações → Recorrências → 

**Campos:**
| Campo | O que preencher |
|---|---|
| **Descrição** | "Salário João", "Aluguel Escritório" |
| **De/Para** | Quem paga/recebe (deve existir no Cadastro) |
| **Projeto** | Projeto administrativo para despesas internas |
| **Tipo** | Serviço, Receita, Despesa Operacional |
| **Conta Origem** | Onde cria (recomendação: Contas a Pagar) |
| **Conta Destino** | Banco real (ex: C6 Bank) |
| **Departamento** | Administrativo, Arquitetura, Marketing... |
| **Classificação** | Plano de contas (Mão de Obra > Fixa > Funcionários) |
| **Valor** | Se varia, coloque média (ajuste depois) |
| **Vezes** | 12 = anual, 6 = semestral |
| **Vencimento** | Dia fixo (ex: todo dia 10) |
| **Status** | Ativo = continua gerando. Desativar = para de gerar |
""",

    # Financeiro Lançamentos: exemplo em itálico + correções (parcelá, vaí)
    "c_financeiro_s3": """# Lançamentos Avulsos

Para despesas ou receitas **que não se repetem**.

*Exemplos: Compra de notebook, manutenção, pagamento único.*

**Criar:** Financeiro → Conta → Novo Lançamento

**Campos:**
| Campo | Descrição |
|---|---|
| **Realizado** | Data efetiva (pode ficar em branco até a baixa) |
| **Emissão** | Data de criação |
| **Vencimento** | Data prevista de pagamento |
| **Descrição** | "Compra de Notebook", "Manutenção Ar" |
| **Valor** | Valor da parcela (se parcelado, valor de cada parcela) |
| **Forma Pgto** | Boleto, Transferência, PIX, Dinheiro, Cheque |
| **Doc. Interno** | NF emitida, número de boleto |
| **Doc. Externo** | NF do fornecedor, boleto recebido |
| **Conta Destino** | Banco para onde vai após conciliação |
| **De/Para** | Quem está envolvido (use cadastro existente) |
| **Departamento** | Centro de custo |
| **Classificação** | Plano de contas (3 níveis) |
| **Projeto** | Administrativo (interno) ou projeto de cliente |
| **Etapa** | Apenas para projetos de clientes |
""",
}


def main():
    db = Database("training.db")
    db.initialize()

    for cid, content in UPDATES.items():
        db.execute(
            "UPDATE step_contents SET content_data = ? WHERE id = ?",
            (content, cid),
        )

    # Correções pontuais no tarefas s5 (Passó, Apróximação) + exemplo itálico
    row = db.execute(
        "SELECT content_data FROM step_contents WHERE id = 'c_tarefas_s5'"
    ).fetchone()
    if row:
        t = row["content_data"]
        t = t.replace("**Passó a passo:**", "**Passo a passo:**")
        t = t.replace(
            "- Exemplos: Reunião de Apróximação, Levantamento, Estudo Preliminar, Executivo, Apresentação, Renderização",
            "- *Exemplos: Reunião de Aproximação, Levantamento, Estudo Preliminar, Executivo, Apresentação, Renderização*",
        )
        db.execute(
            "UPDATE step_contents SET content_data = ? WHERE id = 'c_tarefas_s5'", (t,)
        )

    # Correções no filtros s0 (Periodo) e s1 (Contem, posicao, Comeca, NAO, Pisó)
    row = db.execute("SELECT content_data FROM step_contents WHERE id = 'c_filtros_s0'").fetchone()
    if row:
        t = row["content_data"].replace("Periodo entre", "Período entre")
        db.execute("UPDATE step_contents SET content_data = ? WHERE id = 'c_filtros_s0'", (t,))

    row = db.execute("SELECT content_data FROM step_contents WHERE id = 'c_filtros_s1'").fetchone()
    if row:
        t = row["content_data"]
        t = t.replace("Contem \"texto\" em qualquer posicao", "Contém \"texto\" em qualquer posição")
        t = t.replace("Comeca com", "Começa com")
        t = t.replace("NAO contém", "NÃO contém")
        t = t.replace("Pisó", "Piso")
        db.execute("UPDATE step_contents SET content_data = ? WHERE id = 'c_filtros_s1'", (t,))

    db.commit()
    db.close()
    print("Exemplos padronizados e acentos corrigidos.")


if __name__ == "__main__":
    main()
