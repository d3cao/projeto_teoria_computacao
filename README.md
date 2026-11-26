# Triagem Sequencial de Extratos Vegetais

## Requisitos

- Python 3.10 ou superior.

O projeto utiliza exclusivamente a biblioteca padrão do Python, não sendo necessária a instalação de dependências externas.

## 1. Configuração

Clone o repositório:

```bash
git clone https://github.com/d3cao/projeto_teoria_computacao.git
cd projeto_teoria_computacao
```

Os parâmetros experimentais estão disponíveis no arquivo `parameters.json`. Nele podem ser alteradas as categorias, os limites de discretização, os parâmetros estatísticos da geração sintética e o critério de viabilidade molecular.

## 2. Geração dos dados sintéticos

```bash
python main.py generate
```

Por padrão, serão gerados:

- `data/train.csv`: 2.000 amostras de treinamento.
- `data/test.csv`: 500 amostras de teste.

É possível personalizar o tamanho dos datasets e a semente pseudoaleatória:

```bash
python main.py generate --seed 42 --train-size 5000 --test-size 1000
```

A utilização da mesma semente e dos mesmos parâmetros permite reproduzir os dados gerados.

## 3. Inferência da máquina de Moore

```bash
python main.py infer data/train.csv
```

A máquina inferida será armazenada em `data/moore.json`.

Por padrão, são utilizados três níveis de discretização e suporte mínimo de três amostras para descarte.

Para utilizar cinco níveis:

```bash
python main.py infer data/train.csv --levels 5
```

Para modificar o suporte mínimo:

```bash
python main.py infer data/train.csv --min-support 10
```

## 4. Avaliação da máquina

```bash
python main.py evaluate data/moore.json data/test.csv
```

Os resultados individuais serão armazenados em `data/decisions.csv`, contendo:

| Coluna | Descrição |
|---|---|
| `id` | Identificador da amostra. |
| `decision` | Recomendação de continuidade (`ADVANCE`) ou descarte (`DISCARD`). |
| `discard_layer` | Camada em que ocorreu o descarte, quando aplicável. |
| `viable` | Viabilidade determinada pelo resultado molecular. |
| `false_discard` | Indica se uma amostra viável foi descartada indevidamente. |

O terminal também apresenta a quantidade de amostras avaliadas, os descartes realizados e a taxa de falsos descartes.

## 5. Execução completa

### Três níveis de discretização

```bash
python main.py generate
python main.py infer data/train.csv --levels 3
python main.py evaluate data/moore.json data/test.csv
```

### Cinco níveis de discretização

```bash
python main.py infer data/train.csv --levels 5
python main.py evaluate data/moore.json data/test.csv
```

Para preservar os resultados de diferentes experimentos, utilize caminhos de saída distintos:

```bash
python main.py infer data/train.csv --levels 5 --output data/moore_5.json
python main.py evaluate data/moore_5.json data/test.csv --output data/decisions_5.csv
```

## 6. Ajuda

Para consultar todos os comandos e argumentos disponíveis:

```bash
python main.py --help
python main.py generate --help
python main.py infer --help
python main.py evaluate --help
```

## Observações

- Os comandos devem ser executados a partir da raiz do repositório.
- Os arquivos de saída existentes são sobrescritos durante novas execuções.
- Após modificar os parâmetros experimentais, execute novamente as etapas de geração, inferência e avaliação.
- Os dados são sintéticos e os parâmetros experimentais ainda estão sujeitos à revisão.