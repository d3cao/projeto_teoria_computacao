# Validação computacional dos módulos 3 e 4

## Escopo e ambiente

A versão validada foi o commit `d416d71977e7133250f98e3ad0a82938a21ea7dd`. A execução usou Windows, Python 3.13.3, Matplotlib 3.11.2 e Graphviz 14.1.5. O escopo inclui o escore e o ranking (módulo 3), a avaliação comparativa e o relatório (módulo 4), e a regressão do gerador, do discretizador e da máquina de Moore usados por esses módulos.

| Configuração | Dados e uso |
|---|---|
| Base versionada | `data/train.csv` com 2.000 amostras e `data/test.csv` com 500. A geração padrão usa a semente 42. A regressão usou três e cinco níveis e suporte mínimo 3. |
| Piloto | `experiments/pilot.json`, sementes 42 e 43, treinos de 100 e 200 amostras e 50 amostras de teste por semente. Foram usados três e cinco níveis, suporte mínimo 3 e os perfis `uniform` e `fps_and_dna`. |
| Caso de denominador nulo | Especificação temporária com semente 42, uma amostra em cada base, três níveis e suporte mínimo 3. |

As três configurações usaram `parameters.json`. As saídas ficaram em diretórios temporários.

## Geração sintética

A geração padrão reproduziu os dois CSVs em memória. Reduzir o treino de 2.000 para 100 amostras preservou o teste e manteve as 100 primeiras linhas do treino. Reduzir o teste de 500 para 25 preservou o treino e as 25 primeiras linhas do teste. A semente 43 produziu bases diferentes das da semente 42. A inspeção do gerador confirmou que treino e teste usam duas instâncias de `Random`, inicializadas com sementes derivadas separadamente.

| Verificação | Treino | Teste |
|---|---:|---:|
| Correlação de Pearson entre fenóis e FPS | 0,6424 | 0,5407 |
| Correlação de Pearson entre DPPH e FPS | −0,3209 | −0,2539 |
| Amostras com FPS > 6 e DNA abaixo do limiar | 622 | 173 |
| Amostras com FPS > 6 e UV abaixo de 0,4 | 249 | 62 |
| Viáveis pelo critério `dna >= 0.6` | 884 | 192 |

Todos os rótulos `viable` coincidiram com o critério de DNA. As contagens de UV baixo e DNA abaixo do limiar descrevem os desfechos simulados. Elas incluem os efeitos do ruído e não isolam os eventos internos de perda aleatória do gerador.

## Discretização e máquina de Moore

Foram conferidos valores imediatamente abaixo, iguais e acima de cada corte numérico de fenóis, DPPH, FPS e UV nos dois níveis de granularidade. No discretizador, fenóis iguais a 150 e DPPH igual a 500 permanecem na faixa inferior ao último corte. FPS igual a 6 entra na faixa de discretização que começa em 6. O baseline usa a leitura numérica e descarta esse valor.

Os rótulos foram recontados por prefixo observado. A saída `DISCARD` coincidiu com os prefixos das camadas 4 e 5 que tinham pelo menos três inviáveis e nenhum viável. Houve zero falsos descartes no treino. Cada estado apresentou uma transição por símbolo para um estado existente. Extensões inéditas dos prefixos observados levaram a `continuation`, que emite `ADVANCE`.

| Níveis | Rastros admissíveis com saídas iguais | Estados antes e depois | Transições completas antes e depois | Transições fora de `continuation` antes e depois |
|---|---:|---:|---:|---:|
| 3 | 243 de 243 | 206 / 59 | 3.090 / 885 | 204 / 130 |
| 5 | 675 de 675 | 348 / 82 | 6.612 / 1.558 | 346 / 217 |

A comparação pré e pós-fusão inclui a saída do estado inicial e todas as saídas subsequentes. A contagem de transições usa pares de origem e símbolo. As arestas agrupadas por destino no diagrama podem representar vários desses pares.

## Escore e ranking

O recálculo partiu das leituras sintéticas e da tabela do piloto. Para cada aprovado, foram recalculados os seis componentes, a média ponderada e a posição em cada perfil. As 300 linhas coincidiram com `rankings.csv`. O perfil `uniform` reproduziu a média simples. O perfil `fps_and_dna` usou peso 2 para FPS e DNA e peso 1 nas outras camadas. Um caso com peso zero foi rejeitado. Duas amostras com o mesmo escore receberam a mesma posição, com posições consecutivas entre grupos de empate.

No escore de fenóis, `inclusive_upper: [150]` manteve a leitura exata de 150 na faixa intermediária. Para DPPH, foram exercitados os dois cortes do piloto, imediatamente abaixo, no valor exato e imediatamente acima, tanto com a convenção padrão quanto com ambos os cortes em `inclusive_upper`.

| Corte de DPPH | Antes / no corte / depois, padrão | Antes / no corte / depois, inclusivo na faixa inferior |
|---|---|---|
| 100 | 1 / 0,5 / 0,5 | 1 / 1 / 0,5 |
| 250 | 0,5 / 0 / 0 | 0,5 / 0,5 / 0 |

Uma tabela com pontuações crescentes para DPPH foi rejeitada. Os dois perfis usaram a mesma coorte de amostras que avançaram e eram viáveis por DNA. Em uma execução anterior do piloto, os CSVs de decisão foram idênticos com e sem o escore. No piloto versionado, o perfil alternativo mudou 94 das 150 posições comparadas por execução e amostra.

## Avaliação experimental e reconciliação dos arquivos

Cada semente gerou um teste comum às três políticas. Foram conferidos os identificadores, os rótulos e as decisões das 600 linhas do piloto. A decisão de referência da Moore foi obtida por contagem direta dos prefixos do treino, e os dois baselines foram recalculados sobre as leituras. Um caso controlado com amostra viável e FPS igual a 6 confirmou descarte na camada 4 e marcação de falso descarte.

- Falsos descartes usam como denominador os viáveis por DNA. A eficiência usa os inviáveis por DNA. As duas métricas foram conferidas no total e por ponto de decisão.
- O descarte na camada 4 poupa UV e DNA. O descarte na camada 5 poupa DNA. As taxas por ensaio usam o total de amostras e a taxa combinada usa o dobro desse total. O intervalo ilustrativo em dias-ensaio multiplica o número de execuções evitadas por 1 e por 2.
- As taxas com denominador zero saíram vazias no CSV. No caso com uma semente e uma amostra, 15 das 99 médias ficaram vazias por ausência de observações válidas. O desvio-padrão amostral ficou vazio nas 99 linhas por haver menos de duas observações válidas.

O recálculo conferiu as 12 linhas por semente do piloto e as 246 linhas do resumo, das quais 72 continham diferenças pareadas. Para cada métrica, a média foi obtida pela soma dividida pelo número de valores válidos, e o desvio-padrão amostral pela raiz da soma dos quadrados dos desvios dividida por `n - 1`. Cada delta foi calculado como Moore menos baseline dentro da mesma semente antes da agregação. Foram comparados todos os campos numéricos dessas linhas com tolerância absoluta e relativa de `1e-12`, incluindo o número de repetições válidas e os campos vazios. Não houve divergências.

Os valores das matrizes `comparison.csv` e `topology.csv` coincidiram com os resumos recalculados. O ranking replicado no relatório foi idêntico ao CSV do experimento. Os escores, as posições e a variação das posições nas 150 linhas de `rank_changes.csv` também foram conferidos. `manifest.json` coincidiu com os parâmetros e a grade executada, e `moore.json` coincidiu com a máquina selecionada na especificação. Em verificações complementares, `[0, 42]` foi aceito e reproduziu as saídas, enquanto `[42, -42]` e `[42, 42]` foram rejeitados antes de criar o diretório de resultados.

## Relatórios e figuras

Matplotlib e Graphviz renderizaram nove SVGs no piloto versionado. O SVG da Moore continha os 54 estados e os 150 pares de origem e destino da máquina selecionada, além do marcador de entrada e da sua seta. Em um piloto de visualização anterior, com sementes 42 e 43, treinos de 100, 500 e 2.000 e teste de 150 por semente, os pontos e as barras de desvio-padrão foram confrontados com `metrics_summary.csv`. As frequências dos histogramas coincidiram com as faixas de escore do CSV de ranking, e o diagrama exibiu as arestas tracejadas de continuidade.

## Resultados preliminares na base versionada

| Política | Falsos descartes (de 192) | Descartes corretos (de 308) | UV poupados | DNA poupados | Dias-ensaio |
|---|---:|---:|---:|---:|---:|
| Sem poda | 0 (0,00%) | 0 (0,00%) | 0 | 0 | 0 |
| Corte único de FPS > 6 | 19 (9,90%) | 135 (43,83%) | 154 | 154 | 308 a 616 |
| Moore, três níveis | 2 (1,04%) | 14 (4,55%) | 5 | 16 | 21 a 42 |
| Moore, cinco níveis | 4 (2,08%) | 29 (9,42%) | 9 | 33 | 42 a 84 |

O corte de FPS poupou mais ensaios e perdeu mais viáveis. A Moore de cinco níveis poupou mais ensaios que a de três, com dois falsos descartes adicionais. O fluxo sem poda preservou todos os viáveis e executou as etapas onerosas para todas as amostras. Dias-ensaio expressam uma soma ilustrativa de trabalho. O tempo de calendário depende do paralelismo.

## Reprodução

Execute a partir da raiz do repositório, com Matplotlib no ambiente Python e `dot` no `PATH`. Use diretórios de saída novos.

```powershell
python --version
python -B -c "import matplotlib; print(matplotlib.__version__)"
dot -V
python -B main.py experiment --spec experiments/pilot.json --output-dir results/validation-pilot
python -B main.py report --experiment-dir results/validation-pilot --output-dir results/validation-report
python -B main.py infer data/train.csv --levels 3 --min-support 3 --output results/validation-pilot/moore_3.json
python -B main.py evaluate results/validation-pilot/moore_3.json data/test.csv --output results/validation-pilot/decisions_3.csv
python -B main.py infer data/train.csv --levels 5 --min-support 3 --output results/validation-pilot/moore_5.json
python -B main.py evaluate results/validation-pilot/moore_5.json data/test.csv --output results/validation-pilot/decisions_5.csv
```

As verificações adicionais foram executadas com scripts inline em `python -B -`. Para repetir a reconciliação, agrupe `decisions.csv` por semente, execução e política, derive as contagens a partir de `discard_layer` e `viable` e compare com `metrics_by_seed.csv`. Recalcule as estatísticas com esses valores e alinhe os baselines pela semente ao obter os deltas. Confira `metrics_summary.csv`, `comparison.csv` e `topology.csv`. Para repetir a verificação formal, use `infer_moore` com e sem `merge_states` e percorra o produto cartesiano do alfabeto por camada. Para o escore, use `math.nextafter` nos cortes e compare os componentes, a média e a posição com o ranking exportado.

## Limitações

As bases são sintéticas e os parâmetros do gerador e do escore são provisórios. A revisão não inclui dados de laboratório nem a bateria definitiva do artigo. As correlações e falhas tardias foram verificadas nas bases indicadas. A separação observada entre os fluxos pseudoaleatórios foi verificada pela geração e pela inspeção do código, sem teste estatístico de independência.

O zero observado no treino não se repetiu no teste versionado. A equivalência foi verificada nos rastros admissíveis das duas máquinas de referência. A minimalidade global da máquina está fora dessa verificação. As fronteiras do escore foram testadas nos casos documentados e a reconciliação integral se aplica aos CSVs das execuções indicadas, com os formatos e cenários cobertos pelo piloto.
