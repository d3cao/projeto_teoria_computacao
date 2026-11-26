# Triagem Sequencial de Extratos Vegetais

## Requisitos

- Python 3.10 ou superior.

O núcleo usa a biblioteca padrão do Python. A renderização dos relatórios usa Matplotlib e Graphviz.

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

## 6. Experimento comparativo

Salve uma especificação JSON. O exemplo abaixo é para um piloto e pressupõe
que o arquivo JSON está no mesmo diretório de `parameters.json`.

```json
{
  "config": "parameters.json",
  "seeds": [42, 43],
  "train_sizes": [100, 200],
  "test_size": 50,
  "levels": [3, 5],
  "min_support": 3
}
```

```bash
python main.py experiment --spec pilot.json --output-dir results/pilot
```

O diretório de saída precisa ser novo. Em cada semente, todas as políticas usam
o mesmo teste, e os treinos menores usam subconjuntos iniciais do treino maior.
Os baselines sem poda e com corte estrito `FPS > 6` são avaliados uma vez por semente.

| Arquivo | Conteúdo |
|---|---|
| `decisions.csv` | Decisão por execução, política e amostra. |
| `metrics_by_seed.csv` | Contagens, taxas de descarte, economia de ensaios e compactação da Moore. |
| `metrics_summary.csv` | Média, desvio-padrão amostral e número de repetições válidas por métrica. Quando `baseline` está preenchido, a linha resume a diferença entre a taxa da Moore e a do baseline na mesma semente. |
| `manifest.json` | Configuração efetiva, sementes, tamanhos e versão do Python. Gravado ao concluir a execução. |

As taxas usam a escala de 0 a 1, e os deltas usam a mesma unidade. Células vazias
indicam valores indefinidos ou campos que não se aplicam à política. A economia
expressa execuções de ensaios que seriam evitadas pelo primeiro descarte.

## 7. Escore, ranking e relatórios

Para incluir o ranking, acrescente uma seção `score` à especificação do
experimento. O exemplo abaixo contém pontuações e pesos ilustrativos para o piloto.

```json
{
  "ccd": {"TRACE": 0, "MODERATE": 0.5, "RICH": 1},
  "bands": {
    "phenols": {"thresholds": [50, 150], "scores": [0, 0.5, 1]},
    "dpph": {"thresholds": [100, 250], "scores": [1, 0.5, 0]},
    "fps": {"thresholds": [6, 15], "scores": [0, 0.5, 1]},
    "uv": {"thresholds": [0.4, 0.7], "scores": [0, 0.5, 1]},
    "dna": {"thresholds": [0.6, 0.8], "scores": [0, 0.5, 1]}
  },
  "profiles": {"fps_and_dna": {"fps": 2, "dna": 2}}
}
```

O objeto acima é o valor de `score`. Cada corte pertence à faixa superior e
`scores` tem um elemento a mais que `thresholds`. As pontuações ficam entre 0 e 1.
As de DPPH decrescem ou se mantêm com o IC₅₀. Cada peso deve ser positivo e tem
valor padrão 1. O perfil `uniform` está sempre presente. `rankings.csv` lista as
seis pontuações, o escore e a posição em cada perfil para as amostras viáveis
encaminhadas pela Moore. Empates compartilham a mesma posição.

Para exportar o JSON da máquina ilustrada, acrescente à especificação um campo
`diagram_run` com uma combinação da bateria, por exemplo
`{"seed": 42, "levels": 3, "train_size": 200}`.

```bash
python main.py report --experiment-dir results/pilot --output-dir results/pilot-report
```

O relatório usa um diretório novo. Ele gera `comparison.csv` e `topology.csv`
e inclui `rankings.csv` e `rank_changes.csv` quando o escore está configurado.
As mudanças de posição usam o perfil `uniform` da mesma execução como referência.
Valores positivos em `positions_gained` indicam avanço no ranking.

Instale Matplotlib com `python -m pip install matplotlib` para renderizar as
curvas de sensibilidade e distribuições do escore em SVG. As barras das curvas
mostram o desvio-padrão amostral entre sementes. O relatório gera `moore.dot`
quando `diagram_run` está configurado. Com Graphviz instalado e `dot` no `PATH`,
também gera `moore.svg`. As arestas tracejadas apontam para o estado de continuidade.
Quando falta um renderizador, o comando informa a dependência e entrega as
tabelas e o DOT disponível.

## 8. Ajuda

Para consultar todos os comandos e argumentos disponíveis:

```bash
python main.py --help
python main.py generate --help
python main.py infer --help
python main.py evaluate --help
python main.py experiment --help
python main.py report --help
```

## Observações

- Os comandos devem ser executados a partir da raiz do repositório.
- Os arquivos de saída existentes são sobrescritos durante novas execuções.
- Após modificar os parâmetros experimentais, execute novamente as etapas de geração, inferência e avaliação.
- Os dados são sintéticos e os parâmetros experimentais ainda estão sujeitos à revisão.
