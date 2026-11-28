# Triagem Sequencial de Extratos Vegetais

As evidências computacionais e os resultados preliminares da pesquisa estão no [registro técnico-científico](docs/report.md).

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

### Como alterar os parâmetros da máquina

Para experimentar novos valores, edite `parameters.json` em um editor de texto.

| Campo | O que controla |
|---|---|
| `ccd` e `simulation.ccd_thresholds` | Nomes das três categorias de CCD e os dois cortes usados para gerá-las, na mesma ordem. |
| `thresholds` | Cortes usados pela Moore para discretizar as leituras. Use dois para fenóis e UV e quatro para DPPH e FPS, em ordem crescente e sem repetição. A opção `--levels 3` agrupa as cinco faixas de DPPH e FPS. |
| `dna_threshold` | Valor mínimo de preservação do DNA para rotular a amostra como viável. Use um valor entre 0 e 1. O DNA é o gabarito da avaliação. |
| `simulation` | Parâmetros das leituras sintéticas. As listas de três valores representam nível de base, coeficiente do potencial latente e desvio-padrão do ruído. `log_dpph` e `log_fps` usam escala logarítmica natural. Os demais campos controlam o efeito da UV no DNA e a probabilidade e magnitude das perdas simuladas. |

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

Use [a especificação do piloto](experiments/pilot.json) para conferir o fluxo de
execução. Os parâmetros e pesos desse piloto são ilustrativos. O caminho em
`config` é relativo ao diretório da especificação.

```bash
python main.py experiment --spec experiments/pilot.json --output-dir results/pilot
```

O diretório de saída precisa ser novo. Em cada semente, todas as políticas usam
o mesmo teste. Informe sementes inteiras não negativas e sem repetição.
Em cada semente, os treinos menores usam subconjuntos iniciais do treino maior.
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
`assay_days_saved_min` e `assay_days_saved_max` estimam a soma do trabalho
poupado, considerando 1 a 2 dias por execução evitada de UV ou DNA. A estimativa
é ilustrativa, e o prazo de calendário depende do paralelismo no laboratório.

## 7. Escore, ranking e relatórios

Para incluir o ranking, acrescente uma seção `score` à especificação, como no
[piloto](experiments/pilot.json). Por padrão, cada corte pertence à faixa
superior. Liste em `inclusive_upper` os cortes que devem pertencer à faixa
inferior. No exemplo, fenóis iguais a 150 ficam na faixa intermediária.
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

## 8. Fechamento do protocolo experimental

Antes da bateria do artigo, registre junto da especificação final:

- A origem e o status das categorias de CCD, dos cortes de UV e DNA, das
  correlações simuladas e das frequências de falha tardia, com a fundamentação
  fornecida por João Pedro.
- O gabarito adotado e a definição de descarte correto. A implementação atual
  usa a viabilidade por DNA. Confirme com o laboratório o papel eliminatório de UV.
- As seis tabelas de pontuação, seus cortes inclusivos e a justificativa dos
  perfis de pesos alternativos ao perfil uniforme.
- As sementes reservadas, os tamanhos de treino e teste, os níveis, o suporte
  mínimo e a configuração da máquina escolhida para a figura.
- Os critérios de interpretação dos falsos descartes por ponto, do equilíbrio
  entre eficiência e economia e das mudanças de posição entre perfis. Confirme
  o formato de diagrama exigido pelo orientador.

## 9. Ajuda

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
