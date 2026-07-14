# DOit Training

Plataforma de treinamento interativo do sistema DOit, construída em [Streamlit](https://streamlit.io/).
Organiza o conteúdo em módulos temáticos (Dashboard, Agenda, Projetos, Financeiro, Tarefas, E-mail e mais), com navegação passo a passo, ramificações e acompanhamento de progresso.

## Requisitos

- Python 3.9+
- Dependências em `requirements.txt`

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

O app abre em `http://localhost:8501`.

## Estrutura

```
doit-training/
├── app.py               # Ponto de entrada e roteamento
├── models/              # Modelos de dados, enums e camada SQLite
├── managers/            # Regras de negócio (progresso, conteúdo, etc.)
├── pages/               # Telas (welcome, lista de módulos, etapas, admin)
├── media/               # Imagens e vídeos, organizados por módulo
├── training.db          # Banco SQLite com todo o conteúdo do treinamento
└── seed_*.py            # Scripts de carga de conteúdo
```

## Conteúdo

Todo o conteúdo do treinamento (textos, imagens, ordenação) fica no banco
`training.db`, que é versionado junto com o projeto. As imagens ficam em
`media/<modulo>/`.

## Observação

Este é um aplicativo Streamlit (servidor Python). Não roda em GitHub Pages,
que serve apenas arquivos estáticos. Para publicar online, use o
[Streamlit Community Cloud](https://share.streamlit.io/) ou outro host que
execute Python.
