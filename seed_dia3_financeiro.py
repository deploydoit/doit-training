"""Adiciona módulo Financeiro com conteúdo do Dia 3."""
import sys
sys.path.insert(0, '.')
from models.database import Database


def seed():
    db = Database("training.db")
    db.initialize()

    mid = "financeiro"
    pid = f"{mid}_main"
    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, 'published', 1)",
        (mid, "Financeiro", "Contas, lançamentos, recorrências, fluxo de caixa e classificações"))
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) VALUES (?, ?, 'Principal', ?)",
        (pid, mid, True))

    _s(db, mid, pid, 0, """# Módulo Financeiro — Visão Geral

Controle centralizado de toda movimentação financeira do escritório:

- 🏦 Contas bancárias
- 📤 Contas a pagar
- 📥 Contas a receber
- 📋 Lançamentos financeiros
- 🔄 Recorrências (despesas fixas)
- 📊 Fluxo de caixa
- 💰 Recebimentos de projetos

**Contas padrão:**
- Contas a Pagar
- Contas a Receber
- Conta Corrente (substitua pelo banco real: C6, Itaú, Santander...)

**Criar nova conta:** Financeiro → Contas → Novo Cadastro → informe o nome

**3 visualizações de lançamentos:**
| Lista | O que mostra |
|---|---|
| **Lista 1** | Dados principais (simplificada) |
| **Lista 2** | + Projeto, centro de custo, forma de pagamento |
| **Lista 3** | Máximo de informações e filtros (conferências) |
""")

    _s(db, mid, pid, 1, """# Recorrências — Despesas Fixas

Para lançamentos que acontecem **todo mês** (evita criar manualmente).

**Exemplos:** Salários, Aluguel, Energia, Internet, Telefonia, Contratos

**Criar:** Financeiro → Operações → Recorrências → ➕

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
""")

    _s(db, mid, pid, 2, """# Fluxo das Recorrências

**Como funciona na prática:**

1. Crie a recorrência → lançamentos são gerados em "Contas a Pagar"
2. No dia do pagamento:
   - Confira vencimento e valor
   - Ajuste se necessário
   - Marque como **pago**
3. O sistema automaticamente:
   - Move para a conta bancária definida
   - Gera um **novo lançamento futuro**

**Alterar valor de apenas um mês:**
- Altere direto no lançamento (não afeta a recorrência)
- Ex: comissão extra, conta de energia mais alta

**Alterar valor permanente:**
- Altere na **ficha da recorrência**
- Todos os lançamentos futuros serão atualizados
- Ex: reajuste salarial, novo aluguel

**Encerrar recorrência** (desligamento, cancelamento):
1. Desative a recorrência
2. Remova lançamentos futuros não utilizados
""")

    _s(db, mid, pid, 3, """# Lançamentos Avulsos

Para despesas ou receitas **que não se repetem**.

**Exemplos:** Compra de notebook, manutenção, pagamento único

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
""")

    _s(db, mid, pid, 4, """# Classificação Financeira e Relatórios

**Estrutura de classificação (3 níveis):**

```
Nível 1: Mão de Obra / Despesas Admin / Receita Operacional
  Nível 2: Fixa / Variável
    Nível 3: Funcionários / Software / Marketing / Equipamentos
```

Personalize conforme o plano de contas da empresa.

**Departamentos (Centros de Custo):**
- Administrativo
- Arquitetura
- Interiores
- Marketing
- (personalizáveis)

**Benefícios da classificação correta:**
A cada lançamento bem classificado, o sistema gera automaticamente:

- 📊 **Fluxo de Caixa** — Entradas × Saídas por período
- 📈 **DRE** — Demonstrativo de Resultado
- 🏢 **Custos por departamento**
- 📐 **Custos por projeto**
- 💼 **Despesas administrativas vs operacionais**
- 💰 **Receitas por categoria**

Essas informações servem de base para **análises financeiras e tomadas de decisão**.

✅ Módulo Financeiro concluído!
""")

    db.commit()
    db.close()
    print("✅ Módulo Financeiro adicionado com conteúdo do Dia 3!")


def _s(db, mid, pid, pos, txt):
    sid = f"{mid}_s{pos}"
    db.execute(
        "INSERT INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, 'content')", (sid, mid, pid, pos))
    db.execute(
        "INSERT INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, 'text', ?, 0)", (f"c_{sid}", sid, txt))


if __name__ == "__main__":
    seed()
