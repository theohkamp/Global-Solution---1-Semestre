# Sistema Aurora - Global Solution FIAP

## Equipe
Christian Theodor Heisterkamp - RM571998

Felippe Santos Roeder - RM571913

Matheus Freitas da Silva Santos - RM574003

Pedro Matteo Benta dos Santos Simplicio - RM573133

Samuel Gissi Nogueira Gonçalves - RM568867

## Problema

A colônia Aurora depende de energia solar, energia eólica, baterias, sensores e módulos essenciais para manter a operação em Marte. O sistema monitora infraestrutura, ambiente e reserva energética para preservar suporte vital, identificar riscos e recomendar ações antes que a situação fique irreversível.

O projeto trabalha com dados simulados em ciclos de 3 horas e demonstra conceitos estudados na fase 3: armazenamento em listas e dicionários, matrizes, fila, pilha, hierarquia, expressões booleanas e regressão linear simples.

## Objetivo

Ler `data/dados.txt`, validar os dados, detectar inconsistências, avaliar ambiente e energia, aplicar mitigações por prioridade, gerar alertas e prever a bateria do próximo ciclo.

## Organização do código

O projeto mantém um único arquivo Python de produção, `src/sistema.py`, organizado internamente em camadas inspiradas em MVC por preferência pessoal. Embora esse padrão não tenha sido abordado diretamente nos últimos módulos da fase, ele foi utilizado somente como forma de separar leitura de dados, regras de negócio e exibição dentro de um único arquivo Python. Não é MVC tradicional completo.

- Model: leitura, conversão, validação, matriz, históricos e hierarquia.
- Controller: regras ambientais, energia, mitigações, alertas, pilha e regressão.
- View: relatório no terminal.
- Main: fluxo principal e tratamento simples de erro.

## Dados simulados

- 6 módulos: `habitacao`, `alimentacao`, `suporte_medico`, `centro_logistico`, `energia`, `laboratorio`.
- 6 ciclos de telemetria.
- 9 eventos.
- Energia em kWh por ciclo de 3 horas.
- Bateria em kWh e percentual.
- Sensores e estados binários com `0` ou `1`.
- Inconsistência proposital da bateria no horário `18:00`.

## Estruturas de dados

| Estrutura | Finalidade | Exemplo no sistema |
| --- | --- | --- |
| Lista | Históricos, alertas, eventos e ações | `historico["bateria"]`, `fila`, `acoes` |
| Fila priorizada | Alertas ordenados por prioridade | `enfileirar_alerta()` e `ordenar_fila_alertas()` |
| Pilha | Eventos críticos recentes, lidos do fim para o início | `pilha_eventos` |
| Dicionário | Módulos, configurações, registros e alertas | `modulos["energia"]`, `config` |
| Tabela hash | Uso conceitual do dicionário Python para busca por chave | acesso rápido por nome do módulo |
| Hierarquia/árvore | Dicionários aninhados da colônia | `criar_hierarquia_colonia()` |
| Matriz | Lista de listas com telemetria por horário | `criar_matriz_telemetria()` |

## Lógica booleana

Crise operacional:

```text
crise_operacional =
    sensores_inseguros
    OR radiacao_critica
    OR pressao_critica
    OR (deficit_energetico AND bateria_baixa)
```

Em linguagem natural: a colônia entra em crise se sensores estiverem inseguros, se radiação ou pressão estiverem críticas, ou se houver déficit energético junto com bateria baixa.

Mitigação permitida:

```text
pode_mitigar =
    modulo_nao_protegido
    AND deficit_energetico
    AND NOT suporte_vital
```

No código, essa ideia aparece na sequência de mitigações: habitação e suporte médico são preservados, enquanto laboratório, energia, centro logístico e alimentação recebem medidas conforme prioridade.

## Regras ambientais

- Temperatura interna normal: 18 a 24 graus Celsius; crítica abaixo de 16 ou acima de 27.
- Temperatura externa normal: -70 a -20 graus Celsius; crítica abaixo de -75 ou acima de -15.
- Radiação normal: até 0,30 mSv; crítica acima de 0,50 mSv.
- Pressão normal: 350 a 400 kPa; crítica abaixo de 300 ou acima de 450.
- Vento acima de 100 km/h: tempestade severa e risco de abrasão.
- Vento acima de 160 km/h: travamento mecânico das turbinas e geração eólica efetiva igual a 0.
- Sensores diferentes de `1`: automações de pouso e decolagem bloqueadas.
- Comunicação abaixo dos limites configurados gera alerta ou crítico.
- Módulos com `estado_binario = 0` geram alerta automático de manutenção. Falhas em habitação ou suporte médico recebem severidade crítica por afetarem módulos vitais.

## Energia e mitigação

```text
energia_disponivel = solar + eolica_efetiva + bateria_kwh
deficit = consumo_atual_modulos - energia_disponivel
```

O sistema separa:

- consumo medido pela telemetria;
- consumo nominal dos módulos;
- consumo atual após mitigação.

Sequência aplicada em crise energética:

1. `laboratorio`: desligamento completo.
2. `energia`: redução parcial, preservando funções críticas.
3. `centro_logistico`: redução parcial e, se necessário, desligamento.
4. `alimentacao`: redução emergencial somente em último caso.
5. `habitacao` e `suporte_medico`: nunca desligados.

As mitigações verificam explicitamente os módulos protegidos antes de qualquer ação. Desligamentos integrais também respeitam o campo `pode_desligar`; reduções parciais continuam permitidas quando o módulo pode reduzir funções não essenciais sem desligar totalmente. A bateria atual também gera alerta direto: abaixo de 35% é alerta, abaixo de 25% é crítico.

Percentuais configuráveis em `data/dados.txt`:

- energia: 30%;
- centro logístico: 50%;
- alimentação: 20%.

## Inconsistência proposital

No horário `18:00`, o arquivo informa:

```text
bateria_kwh = 96
bateria_pct informado = 72
capacidade_total_bateria_kwh = 300
```

O percentual correto é:

```text
96 / 300 * 100 = 32%
```

Essa inconsistência foi inserida propositalmente para testar a validação. O sistema exibe o valor informado, o valor esperado e usa internamente o percentual corrigido no histórico e na regressão.

## Regressão linear

A previsão usa regressão linear simples manual, sem bibliotecas externas.

- Variável independente `x`: número do ciclo.
- Variável dependente `y`: percentual validado da bateria.
- Saídas: inclinação, intercepto, R2 e previsão do próximo ciclo.

Resultado real da execução atual:

```text
Historico: 70.0%, 63.0%, 50.0%, 40.0%, 32.0%, 24.0%
Inclinacao: -9.5143
Intercepto: 79.8000
R2: 0.9929
Previsao: 13.2%
Decisao: corte preventivo influenciado pela regressao
```

## Execução

```bash
python src/sistema.py
```

No Windows:

```bash
py src/sistema.py
```

## Testes

```bash
python -m unittest discover -s tests -v
```

No Windows:

```bash
py -m unittest discover -s tests -v
```

Na auditoria técnica final, `py -m unittest discover -s tests -v` executou 30 testes e todos foram aprovados.

## Exemplo resumido da saída

```text
STATUS GERAL
- CRITICO

3. BALANCO ENERGETICO
- Consumo medido pela telemetria: 380.0 kWh
- Consumo nominal dos modulos: 380.0 kWh
- Consumo atual apos mitigacao: 264.5 kWh
- Energia disponivel: 76.0 kWh | deficit: 188.5 kWh

6. INCONSISTENCIAS DETECTADAS
- 18:00 bateria_pct: informado 72.0, esperado 32.0.

7. PREVISAO DA BATERIA
- Proximo ciclo: 13.2% | decisao: Corte preventivo influenciado pela regressao.
```
## Recomendações geradas

Entre as recomendações automáticas apresentadas pelo sistema estão:

- preservar habitação e suporte médico;
- desligar temporariamente o laboratório em crises energéticas;
- reduzir funções não essenciais do módulo de energia;
- limitar atividades externas em caso de radiação elevada;
- bloquear automações de pouso e decolagem quando os sensores estiverem inseguros;
- programar manutenção preventiva após abrasão prolongada das turbinas;
- solicitar decisão humana caso o déficit permaneça crítico.

## Link do vídeo

## Conclusões e aprendizados

O projeto demonstrou como estruturas fundamentais da linguagem Python podem ser combinadas para interpretar dados operacionais, detectar riscos e fornecer recomendações automáticas. A equipe aplicou listas, fila, pilha, dicionários, hierarquia, matriz, lógica booleana e regressão linear simples em um cenário de monitoramento espacial.

A simulação mostrou a importância de validar dados antes de utilizá-los em decisões críticas. Também evidenciou que módulos vitais devem permanecer protegidos durante crises energéticas e que previsões simples podem auxiliar ações preventivas.
