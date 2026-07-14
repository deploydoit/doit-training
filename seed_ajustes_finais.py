"""Ajustes finais: atas dentro de projetos, visual moderno, filtros, documentos e email."""
import sys
sys.path.insert(0, '.')
from models.database import Database


def seed():
    db = Database("training.db")
    db.initialize()

    # 1. Remover módulo Atas separado (conteúdo fica dentro de Projetos)
    db.execute("DELETE FROM modules WHERE id = 'atas'")

    # 2. Remover módulos Documentos e Email antigos para recriar
    db.execute("DELETE FROM modules WHERE id = 'documentos'")
    db.execute("DELETE FROM modules WHERE id = 'email'")
    db.commit()

    # 3. Adicionar etapa de Atas dentro do módulo Projetos
    _add_atas_to_projetos(db)

    # 4. Recriar Documentos (apenas consulta)
    _mod_documentos(db)

    # 5. Recriar Email (registro + modelos)
    _mod_email(db)

    # 6. Novo módulo: Filtros e Relatórios
    _mod_filtros(db)

    db.commit()
    db.close()
    print("Ajustes concluidos:")
    print("  - Atas movidas para dentro de Projetos")
    print("  - Documentos atualizado (consulta)")
    print("  - E-mail atualizado (registro + modelos)")
    print("  - Filtros e Relatorios adicionado")


def _m(db, mid, title, desc):
    db.execute(
        "INSERT OR IGNORE INTO modules (id, title, description, status, version) "
        "VALUES (?, ?, ?, 'published', 1)", (mid, title, desc))
    pid = f"{mid}_main"
    db.execute(
        "INSERT OR IGNORE INTO paths (id, module_id, name, is_main) "
        "VALUES (?, ?, 'Principal', ?)", (pid, mid, True))
    return pid


def _s(db, mid, pid, pos, txt):
    sid = f"{mid}_s{pos}"
    db.execute(
        "INSERT OR IGNORE INTO steps (id, module_id, path_id, position, step_type) "
        "VALUES (?, ?, ?, ?, 'content')", (sid, mid, pid, pos))
    db.execute(
        "INSERT OR IGNORE INTO step_contents (id, step_id, content_type, content_data, display_order) "
        "VALUES (?, ?, 'text', ?, 0)", (f"c_{sid}", sid, txt))


def _add_atas_to_projetos(db):
    """Adiciona etapa 4 ao módulo projetos com conteúdo de Atas."""
    mid = "projetos"
    pid = f"{mid}_main"
    _s(db, mid, pid, 4, """# Atas de Reuniao

As atas registram reunioes, visitas e alinhamentos diretamente dentro do projeto.

**Acesso:** Projeto  /  Ficha  /  Atas de Reuniao

---

**Criar ata**

| Campo | Descricao |
|---|---|
| Assunto | Tema principal da reuniao |
| Responsavel | Quem registra |
| Data e Hora | Inicio e fim — calcula horas automaticamente |
| Local | Onde ocorreu |
| Visita | Marca para contabilizar no controle de visitas |

**Corpo da ata** — campo livre para decisoes, pendencias, observacoes.

**Participantes Internos** — colaboradores do escritorio.
**Participantes Externos** — clientes, fornecedores (precisam ter cadastro).

**Documentos** — anexe fotos, PDFs, planilhas.

---

**Envio**

- Salvar internamente — apenas para consulta
- Enviar por e-mail — participantes com e-mail sao copiados automaticamente
- Exportar PDF — contem dados, participantes, conteudo e anexos

**Cobranca de Visitas**

1. Configure o valor unitario no projeto (ex: R$ 200,00)
2. Marque visitas para cobranca
3. Sao encaminhadas ao financeiro

**Integracao Agenda  /  Ata:**
Se um evento da Agenda estiver vinculado ao projeto, e possivel gerar a ata diretamente — o sistema reaproveita as informacoes.

Horas da reuniao sao descontadas do saldo contratado. Visitas sao contabilizadas automaticamente.
""")


def _mod_documentos(db):
    p = _m(db, "documentos", "Documentos",
        "Consulte todos os arquivos anexados no sistema em um unico lugar")

    _s(db, "documentos", p, 0, """# Documentos

O modulo Documentos centraliza todos os arquivos existentes no DOit para consulta rapida.

Voce nao cria documentos aqui — eles sao adicionados nos cadastros, projetos e atas.
Este modulo serve para **localizar e filtrar** qualquer arquivo do sistema.

---

**Filtros disponiveis**

- ID Relacionado
- Tipo de documento
- Nome do Arquivo
- Descricao
- Versao
- Data
- Criado Por

---

**Abas de navegacao**

| Aba | Origem dos arquivos |
|---|---|
| Todos | Todos os documentos do sistema |
| Cadastros | Arquivos da Ficha de cadastros |
| Projetos | Arquivos vinculados a projetos |
| Atas de Reuniao | Arquivos anexados em atas |

Todas as abas compartilham os mesmos filtros de pesquisa.

Documentos com data de validade definida geram alertas automaticos na Dashboard quando o vencimento se aproxima.
""")


def _mod_email(db):
    p = _m(db, "email", "E-mail",
        "Consulte e-mails enviados pelo sistema e utilize modelos de envio")

    _s(db, "email", p, 0, """# E-mail

O DOit registra todos os e-mails enviados pelo sistema.
Ele nao recebe e-mails — funciona como ferramenta de envio e historico.

---

**O que voce encontra aqui**

| Aba | Conteudo |
|---|---|
| Meus E-mails | E-mails enviados por voce pelo DOit |
| Todos E-mails | E-mails de todos os usuarios (requer permissao) |
| Ficha | Detalhes do e-mail selecionado |
| Modelos | Templates reutilizaveis para agilizar envios |
| Setup | Configuracao de contas de envio |

---

**Modelos de E-mail**

Modelos sao templates prontos para e-mails recorrentes.

Exemplos de uso: propostas, contratos, cobrancas de etapas, felicitacoes.

- Meus Modelos — criados por voce, privados por padrao
- Modelos Publicos — compartilhados com toda a equipe

Para criar: E-mail  /  Modelos  /  Meus Modelos  /  Novo
Para usar: clique no icone de envio ao lado do modelo — um rascunho e criado com o conteudo preenchido.

E possivel proteger um modelo contra edicoes de outros usuarios.
""")


def _mod_filtros(db):
    p = _m(db, "filtros", "Filtros e Relatorios",
        "Domine os filtros de busca e aprenda a extrair relatorios em PDF e Excel")

    _s(db, "filtros", p, 0, """# Filtros — Datas e Periodos

Os filtros sao a ferramenta mais poderosa do DOit para localizar informacoes.
Funcionam em todos os modulos: Cadastros, Projetos, Financeiro, Tarefas.

---

**Filtros de Data**

| Pesquisa | Resultado |
|---|---|
| DD/MM/AAAA | Data exata |
| DD/MM/AAAA... | A partir dessa data (inclui posteriores) |
| ...DD/MM/AAAA | Ate essa data (inclui anteriores) |
| DD/MM/AAAA...DD/MM/AAAA | Periodo entre as duas datas |

**Exemplos praticos:**

- `01/06/2025` — somente esse dia
- `01/06/2025...` — de 1 de junho em diante
- `...30/06/2025` — ate 30 de junho
- `01/01/2025...31/03/2025` — primeiro trimestre de 2025
""")

    _s(db, "filtros", p, 1, """# Filtros — Campos de Texto

Use estes operadores em qualquer campo de texto do sistema.

---

| Pesquisa | Resultado |
|---|---|
| texto | Contem "texto" em qualquer posicao |
| texto* | Comeca com "texto" |
| *texto | Termina com "texto" |
| texto1 \\|\\| texto2 | Contem "texto1" OU "texto2" |
| !=texto | NAO contem "texto" |

**Exemplos praticos:**

- `Maria` — todos os registros que contem "Maria"
- `Arq*` — comeca com "Arq" (Arquitetura, Arquivo...)
- `*ltda` — termina com "ltda"
- `Piso || Porcelanato` — contem Piso OU Porcelanato
- `!=Cancelado` — exclui registros com "Cancelado"
""")

    _s(db, "filtros", p, 2, """# Filtros — Numeros e Diversos

**Campos numericos**

| Pesquisa | Resultado |
|---|---|
| 1000 | Igual a 1000 |
| <1000 | Menor que 1000 |
| >1000 | Maior que 1000 |
| 1000...2000 | De 1000 a 2000 |
| 1000 \\|\\| 2000 | Exatamente 1000 ou 2000 |

---

**Filtros especiais (muito uteis)**

| Pesquisa | Resultado |
|---|---|
| * ou ! | Campos preenchidos (nao vazios) |
| = | Campos vazios |

**Quando usar:**

- `*` no campo Responsavel — mostra apenas tarefas que ja tem responsavel
- `=` no campo Responsavel — mostra apenas tarefas SEM responsavel (utile para delegacao em massa)
- `>0` no campo Valor — mostra apenas lancamentos com valor preenchido
""")

    _s(db, "filtros", p, 3, """# Relatorios

O DOit permite extrair relatorios em PDF e Excel em diversos modulos.

---

**Onde extrair relatorios**

| Modulo | Tipo | O que gera |
|---|---|---|
| Cadastros | PDF / Excel | Listagem de cadastros com filtros aplicados |
| Projetos  /  Geral | PDF / Excel | Lista de projetos |
| Projetos  /  Horas | Excel | Horas por projeto, colaborador, periodo |
| Projetos  /  Despesas | Excel | Despesas por projeto |
| Projetos  /  $ | PDF | Custo de Projetos |
| Tarefas | Excel | Tarefas com filtros aplicados |
| Financeiro | Excel | Lancamentos, fluxo de caixa |
| Agenda  /  Lista | Excel | Eventos filtrados |
| Listas | Excel | Contatos de uma lista de e-mail |

---

**Como gerar**

1. Aplique os filtros desejados na listagem
2. Clique no icone de PDF ou Excel (barra superior)
3. O relatorio e gerado com base nos filtros ativos

Os relatorios respeitam o nivel de acesso do usuario — voce so exporta o que consegue visualizar.

Alguns relatorios exigem permissao especifica (ex: financeiro, custos de projeto).
""")


if __name__ == "__main__":
    seed()
