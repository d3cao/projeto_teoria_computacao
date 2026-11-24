# Triagem de extratos com Máquina de Moore

Implementação dos módulos 1 e 2 em Python 3.10+ com a biblioteca padrão.
Os CSVs incluídos têm 2.000 amostras de treino e 500 de teste, geradas
com fluxos pseudoaleatórios distintos derivados da semente 42.

## Executar

```sh
cd /home/d3cao/Documents/projeto_teoria_computacao
python3 -m unittest -v
python3 triagem.py treinar exemplo_treino.csv --saida moore.json
python3 triagem.py avaliar moore.json exemplo_teste.csv --saida decisoes_teste.csv
python3 triagem.py avaliar moore.json exemplo_treino.csv --saida decisoes_treino.csv
```

Para regenerar os dois exemplos, execute `python3 triagem.py gerar` na pasta do
projeto. O comando regrava os CSVs de exemplo. Use `--treino` e `--teste` para
escolher outros nomes e `--semente`, `--n-treino` e `--n-teste` para variar a geração.
No treino, use `--niveis 5` para as faixas detalhadas ou `--kmin` para ajustar o
suporte mínimo. Os padrões são três níveis e suporte mínimo de três amostras.
O JSON da máquina armazena a configuração usada no treino para aplicar a mesma
discretização na avaliação.

## Dados e decisões

Cada linha informa o identificador, a categoria de CCD, fenóis em mg EAG/g,
DPPH (IC50) em µg/mL, FPS, resposta UV e preservação de DNA em escala de 0 a 1
e o rótulo `viavel` (0 ou 1). O gerador usa um fator compartilhado com ruído
independente por leitura. Eventos probabilísticos podem reduzir UV e DNA
mesmo com FPS acima de 6. A preservação de DNA é comparada com o corte do JSON
para atribuir o rótulo. Os parâmetros de CCD, UV, DNA e os coeficientes da
simulação são provisórios. Ao mudar o corte de DNA, regenere os CSVs.

A máquina recebe CCD, fenóis, DPPH, FPS e UV nessa ordem. Em cada prefixo
observado, o treino conta quantas amostras são viáveis e inviáveis. Após FPS
ou UV, um estado recomenda descarte se todas as amostras forem inviáveis e
atingirem o suporte mínimo. Uma transição inédita leva a um estado de avanço
que mantém essa recomendação. Na avaliação, o percurso para no primeiro
descarte. O DNA fornece o gabarito para calcular falsos descartes.

O modelo exportado contém estados, estado inicial, alfabetos, transições e
saídas, além das contagens agregadas por estado e do total de estados antes e
depois da fusão. Ambos os totais incluem o estado de continuidade.

## Resultados com os exemplos incluídos

| Níveis | Estados antes → depois | Falsos descartes no treino | Falsos descartes no teste |
| --- | --- | --- | --- |
| 3 | 206 → 59 | 0/884 (0%) | 2/192 (1,04%) |
| 5 | 348 → 82 | 0/884 (0%) | 4/192 (2,08%) |

As taxas usam o total de amostras viáveis de cada base como denominador.
Os resultados se referem aos dados sintéticos com semente 42 e suporte mínimo 3.
