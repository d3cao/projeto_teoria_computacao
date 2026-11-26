# Evidências computacionais e resultados preliminares da triagem

A comparação com os baselines e a análise de pesos são resultados preliminares de uma simulação com parâmetros provisórios. A verificação formal examina a regra de descarte e os efeitos da fusão de estados nas máquinas inferidas para esse cenário.

## Metodologia e dados sintéticos

A geração padrão com semente 42 reproduziu as 2.000 amostras de treino e as 500 de teste versionadas. O gerador deriva os dois fluxos pseudoaleatórios separadamente. Nos casos verificados, reduzir o treino preservou o teste, reduzir o teste preservou o treino e os conjuntos menores coincidiram com o início dos conjuntos maiores. A semente 43 gerou novas amostras.

| Característica observada | Treino | Teste |
|---|---:|---:|
| Correlação de Pearson entre fenóis e FPS | 0,6424 | 0,5407 |
| Correlação de Pearson entre DPPH e FPS | −0,3209 | −0,2539 |
| FPS > 6 e DNA abaixo do limiar de viabilidade | 622 | 173 |
| FPS > 6 e UV abaixo de 0,4 | 249 | 62 |
| Viáveis por DNA | 884 | 192 |

Os rótulos coincidiram com o critério molecular simulado, que considera viável uma amostra com índice de preservação do DNA igual ou superior a 0,6. Na base de teste, 173 amostras passaram pelo corte de FPS e ainda assim foram reprovadas pelo critério molecular. A contagem de UV baixo descreve a resposta simulada nesse ensaio. O desfecho eliminatório usado na comparação foi a viabilidade por DNA.

Em cada repetição, a Moore e os baselines foram avaliados sobre as mesmas amostras de teste. Os níveis 3 e 5 alteram as faixas de DPPH e FPS. No piloto, treinos de 100 e 200 amostras foram obtidos como prefixos do mesmo treino por semente. O teste teve 50 amostras por semente, com suporte mínimo 3 nas duas granularidades. As comparações agregam diferenças calculadas primeiro dentro da mesma semente. O recálculo a partir das decisões individuais reproduziu as métricas por semente, as médias, os desvios-padrão amostrais e as diferenças pareadas do piloto.

## Evidências computacionais sobre a máquina de Moore

A recontagem dos rótulos por prefixo observado confirmou a regra conservadora nas duas granularidades. O descarte ocorreu somente nos pontos após FPS e UV, quando o prefixo tinha pelo menos três inviáveis e nenhum viável. Houve zero falsos descartes no treino. Cada estado tinha uma transição definida por símbolo, e extensões inéditas dos prefixos observados levaram ao estado de continuidade, que recomenda o avanço da amostra.

A árvore de prefixos completada e a máquina após a fusão tiveram a mesma sequência de saídas, desde o estado inicial, em todos os rastros admissíveis das duas configurações. A compactação foi medida contando cada par de estado de origem e símbolo como uma transição.

| Níveis | Rastros com sequência de saídas igual | Estados antes / depois | Transições completas antes / depois | Transições fora do estado de continuidade antes / depois |
|---|---:|---:|---:|---:|
| 3 | 243 de 243 | 206 / 59 | 3.090 / 885 | 204 / 130 |
| 5 | 675 de 675 | 348 / 82 | 6.612 / 1.558 | 346 / 217 |

Nos dois casos, a fusão reduziu o número de estados e transições, com a mesma sequência de saídas para todos os rastros admissíveis avaliados. O teste de equivalência se restringiu a essas duas máquinas. A minimalidade global está fora do seu alcance.

## Comparação preliminar com os baselines

A base de teste versionada contém 192 viáveis e 308 inviáveis. A taxa de falsos descartes divide os viáveis descartados pelo total de viáveis. A eficiência divide os inviáveis descartados pelo total de inviáveis. O primeiro descarte após FPS poupa UV e DNA. Após UV, poupa apenas DNA. A economia representa ensaios que seriam evitados sob cada política.

| Política | Falsos descartes | Eficiência de descarte | UV poupados | DNA poupados | Dias-ensaio poupados |
|---|---:|---:|---:|---:|---:|
| Sem poda | 0/192 (0,00%) | 0/308 (0,00%) | 0 | 0 | 0 |
| Corte único de FPS > 6 | 19/192 (9,90%) | 135/308 (43,83%) | 154 | 154 | 308 a 616 |
| Moore, três níveis | 2/192 (1,04%) | 14/308 (4,55%) | 5 | 16 | 21 a 42 |
| Moore, cinco níveis | 4/192 (2,08%) | 29/308 (9,42%) | 9 | 33 | 42 a 84 |

Para H1, as duas máquinas tiveram falsos descartes nesse teste. Com três níveis, houve um após FPS e um após UV. Com cinco, houve um após FPS e três após UV. O alvo de 0% se manteve no treino das duas máquinas e foi contrariado no teste versionado.

Para H2, as duas máquinas preservaram mais viáveis que o corte de FPS e descartaram menos inviáveis. A granularidade de cinco níveis evitou mais ensaios que a de três, com dois falsos descartes adicionais. O fluxo sem poda preservou todos os viáveis e encaminhou todas as amostras às etapas onerosas. A estimativa de 1 a 2 dias por ensaio evitado é uma soma ilustrativa de trabalho. O tempo de calendário depende do paralelismo do laboratório.

## Efeito preliminar dos pesos sobre o escore

O escore final é a soma das seis pontuações normalizadas multiplicadas pelos respectivos pesos, dividida pela soma dos pesos. O recálculo independente reproduziu os componentes, os escores e as posições do piloto. Com pesos unitários, a fórmula reproduziu a média simples. A tabela do piloto atribui maior pontuação a valores menores de DPPH. Casos imediatamente abaixo, no valor exato e acima dos cortes confirmaram a convenção adotada para cada faixa, inclusive quando a igualdade é atribuída à faixa inferior.

A comparação de pesos usou a mesma coorte de viáveis encaminhados pela Moore em cada execução. O perfil alternativo, com peso 2 para FPS e DNA e peso 1 para as outras camadas, alterou 94 das 150 posições comparadas. Essas comparações abrangem diferentes configurações e sementes, com reutilização do mesmo teste entre configurações da mesma semente. Para H3, o piloto mostra que a priorização depende do perfil de pesos. A interpretação biológica dessa ordem depende da fundamentação das faixas e dos pesos.

## Alcance dos resultados

O piloto usou as sementes 42 e 43 para verificar a comparação pareada e a sensibilidade do ranking. Na base versionada, a comparação entre três e cinco níveis manteve o mesmo treino, o mesmo teste e o mesmo suporte mínimo. Os resultados observados mostram o efeito da granularidade nessa base. A bateria definitiva permitirá avaliar como esse efeito varia entre sementes e tamanhos de treino.

As correlações e falhas tardias descritas aqui pertencem às bases sintéticas examinadas. Falta validar o comportamento em dados laboratoriais. A bateria definitiva, com parâmetros fundamentados e sementes reservadas, deve quantificar a frequência dos falsos descartes por ponto de decisão, a variação dos ganhos frente aos baselines e a estabilidade do ranking sob os perfis de pesos aprovados.
