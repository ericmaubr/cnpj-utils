# cnpj-utils

Projeto Python para enriquecer planilhas com dados de CNAE por CNPJ, usando:

- API OpenCNPJ com chamadas assincronas
- cache local em SQLite
- classificacao de setor IBGE
- saida em Excel

## Estrutura

```text
.
|-- data/
|   |-- cache/
|   |-- processed/
|   `-- raw/
|-- src/
|   `-- cnpj_utils/
|-- tests/
|-- .pre-commit-config.yaml
`-- pyproject.toml
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

## Uso

Coloque o arquivo de entrada em `data/raw/entrada.xlsx` com a coluna `CNPJ` e rode:

```bash
python -m cnpj_utils
```

Ou com caminhos customizados:

```bash
python -m cnpj_utils --input data/raw/minha_entrada.xlsx --output data/processed/saida.xlsx
```

Para preencher descricoes de CNAE quando a API nao informar:

```bash
python -m cnpj_utils --download-cnae-table
```

Ou usando uma tabela local:

```bash
python -m cnpj_utils --cnae-table data/raw/CNAE_Subclasses_2_3_Estrutura_Detalhada.xlsx
```

## Logging

Logs sao enviados para console e para `logs/cnpj_utils.log` (com rotacao).

```bash
python -m cnpj_utils --log-level DEBUG --log-file logs/pipeline.log
```
