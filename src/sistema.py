from pathlib import Path



# CONFIGURAÇÕES E CONSTANTES


SECOES_OBRIGATORIAS = ["CONFIGURACOES", "MODULOS", "TELEMETRIA", "EVENTOS"]
MODULOS_OBRIGATORIOS = {"habitacao", "alimentacao", "suporte_medico", "centro_logistico", "energia", "laboratorio"}
PROTEGIDOS = {"habitacao", "suporte_medico"}
SEVERIDADES = {"normal", "alerta", "critico", "informativo"}
PRIORIDADE_ALERTA = {"critico": 1, "alerta": 2, "normal": 3, "informativo": 3}

CABECALHOS = {
    "MODULOS": ["nome", "categoria", "prioridade", "estado_binario", "pode_desligar", "consumo_kwh"],
    "TELEMETRIA": [
        "horario", "solar_kwh", "eolica_kwh", "bateria_kwh", "bateria_pct",
        "consumo_total_kwh", "temperatura_interna_c", "temperatura_externa_c",
        "radiacao_msv", "pressao_kpa", "vento_kmh", "sensores_funcionais",
        "qualidade_comunicacao_pct",
    ],
    "EVENTOS": ["horario", "tipo", "modulo", "severidade", "descricao"],
}

CONFIG_PADRAO = {
    "capacidade_total_bateria_kwh": 300,
    "ciclo_horas": 3,
    "limite_bateria_alerta_pct": 35,
    "limite_bateria_critico_pct": 25,
    "limite_comunicacao_alerta_pct": 70,
    "limite_comunicacao_critico_pct": 40,
    "tolerancia_bateria_pct": 1,
    "limite_previsao_alerta_pct": 35,
    "limite_previsao_critico_pct": 25,
    "percentual_reducao_energia": 30,
    "percentual_reducao_centro_logistico": 50,
    "percentual_reducao_alimentacao": 20,
    "tolerancia_consumo_kwh": 80,
}



# MODEL -- LEITURA, CONVERSÃO E VALIDAÇÃO DOS DADOS


def carregar_arquivo(caminho=None):
    caminho = Path(caminho) if caminho else Path(__file__).resolve().parents[1] / "data" / "dados.txt"
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de dados não encontrado: {caminho}")
    return caminho.read_text(encoding="utf-8").splitlines()


def separar_secoes(linhas):
    secoes, atual = {}, None
    for numero, original in enumerate(linhas, 1):
        linha = original.strip()
        if not linha or linha.startswith("#"):
            continue
        if linha.startswith("[") and linha.endswith("]"):
            atual = linha[1:-1].upper()
            secoes[atual] = []
        elif atual:
            secoes[atual].append(linha)
        else:
            raise ValueError(f"Linha {numero}: conteúdo fora de uma seção.")
    return secoes


def partes(linha):
    return [parte.strip() for parte in linha.split(";")]


def validar_cabecalhos(secoes):
    erros = [f"Seção obrigatória ausente ou vazia: [{s}]" for s in SECOES_OBRIGATORIAS if not secoes.get(s)]
    for secao, cabecalho in CABECALHOS.items():
        if secoes.get(secao) and partes(secoes[secao][0]) != cabecalho:
            erros.append(f"Cabeçalho inválido em [{secao}].")
    if erros:
        raise ValueError("\n".join(erros))


def numero(valor, campo, erros, inteiro=False, minimo=None, maximo=None):
    try:
        n = int(valor) if inteiro else float(valor)
    except ValueError:
        erros.append(f"Campo {campo} com valor numérico inválido: {valor}")
        return 0 if inteiro else 0.0
    if minimo is not None and n < minimo:
        erros.append(f"Campo {campo} abaixo do mínimo {minimo}: {n}")
    if maximo is not None and n > maximo:
        erros.append(f"Campo {campo} acima do máximo {maximo}: {n}")
    return n


def converter_configuracoes(linhas):
    erros, lidas = [], {}
    for linha in linhas:
        if "=" in linha:
            chave, valor = [p.strip() for p in linha.split("=", 1)]
            lidas[chave] = valor
        else:
            erros.append(f"Configuração inválida: {linha}")
    config = {chave: numero(lidas.get(chave, valor), chave, erros, minimo=0) for chave, valor in CONFIG_PADRAO.items()}
    return config, erros


def novo_modulo(nome, categoria, prioridade, estado, pode_desligar, consumo):
    return {
        "nome": nome,
        "categoria": categoria,
        "prioridade": prioridade,
        "estado_binario": estado,
        "pode_desligar": pode_desligar,
        "consumo_nominal_kwh": consumo,
        "consumo_atual_kwh": consumo,
        "status_operacional": "ativo",
        "percentual_reducao": 0,
        "motivo_alteracao": "",
    }


def converter_modulos(linhas):
    modulos, erros = {}, []
    for indice, linha in enumerate(linhas[1:], 2):
        campos = partes(linha)
        if len(campos) != len(CABECALHOS["MODULOS"]):
            erros.append(f"Módulo linha {indice} incompleto.")
            continue
        nome, categoria, prioridade, estado, pode_desligar, consumo = campos
        if nome in modulos:
            erros.append(f"Módulo duplicado: {nome}")
        estado_int = numero(estado, f"estado_binario({nome})", erros, inteiro=True)
        if estado_int not in (0, 1):
            erros.append(f"Estado binário inválido no módulo {nome}: {estado_int}")
        pode_desligar_int = numero(pode_desligar, f"pode_desligar({nome})", erros, inteiro=True)
        if pode_desligar_int not in (0, 1):
            erros.append(f"Campo pode_desligar inválido no módulo {nome}: {pode_desligar_int}")
        modulos[nome] = novo_modulo(
            nome, categoria,
            numero(prioridade, f"prioridade({nome})", erros, inteiro=True, minimo=1),
            estado_int,
            pode_desligar_int,
            numero(consumo, f"consumo_kwh({nome})", erros, minimo=0),
        )
    return modulos, erros


def converter_telemetria(linhas):
    registros, erros = [], []
    for indice, linha in enumerate(linhas[1:], 2):
        campos = partes(linha)
        if len(campos) != len(CABECALHOS["TELEMETRIA"]):
            erros.append(f"Telemetria linha {indice} incompleta.")
            continue
        registro = {"horario": campos[0]}
        for campo, valor in zip(CABECALHOS["TELEMETRIA"][1:], campos[1:]):
            if campo == "sensores_funcionais":
                registro[campo] = numero(valor, f"{campo}({campos[0]})", erros, inteiro=True)
            else:
                minimo = None if campo.startswith("temperatura") else 0
                maximo = 100 if campo in ("bateria_pct", "qualidade_comunicacao_pct") else None
                registro[campo] = numero(valor, f"{campo}({campos[0]})", erros, minimo=minimo, maximo=maximo)
        registro["consumo_medido_kwh"] = registro["consumo_total_kwh"]
        if registro["sensores_funcionais"] not in (0, 1):
            erros.append(f"Sensores em {registro['horario']} possuem estado inválido.")
        registros.append(registro)
    return registros, erros


def converter_eventos(linhas):
    eventos, erros = [], []
    for indice, linha in enumerate(linhas[1:], 2):
        campos = partes(linha)
        if len(campos) != len(CABECALHOS["EVENTOS"]):
            erros.append(f"Evento linha {indice} incompleto.")
        else:
            eventos.append(dict(zip(CABECALHOS["EVENTOS"], campos)))
    return eventos, erros


def validar_minimos(config, modulos, telemetrias, eventos):
    fatais, avisos = [], []
    if len(modulos) < 6:
        fatais.append("Mínimo de 6 módulos não atendido.")
    if len(telemetrias) < 6:
        fatais.append("Mínimo de 6 registros de telemetria não atendido.")
    if len(eventos) < 8:
        fatais.append("Mínimo de 8 eventos não atendido.")
    for nome in sorted(MODULOS_OBRIGATORIOS - set(modulos)):
        fatais.append(f"Módulo obrigatório ausente: {nome}")
    for r in telemetrias:
        if r["bateria_kwh"] > config["capacidade_total_bateria_kwh"]:
            avisos.append(f"Bateria em kWh acima da capacidade em {r['horario']}.")
    for e in eventos:
        if e["severidade"] not in SEVERIDADES:
            avisos.append(f"Evento com severidade inválida: {e['severidade']}")
        if e["modulo"] not in modulos:
            avisos.append(f"Evento cita módulo inexistente: {e['modulo']}")
    if fatais:
        raise ValueError("\n".join(fatais))
    return avisos


def carregar_dados(caminho=None):
    secoes = separar_secoes(carregar_arquivo(caminho))
    validar_cabecalhos(secoes)
    config, e1 = converter_configuracoes(secoes["CONFIGURACOES"])
    modulos, e2 = converter_modulos(secoes["MODULOS"])
    telemetrias, e3 = converter_telemetria(secoes["TELEMETRIA"])
    eventos, e4 = converter_eventos(secoes["EVENTOS"])
    avisos = validar_minimos(config, modulos, telemetrias, eventos)
    return config, modulos, telemetrias, eventos, e1 + e2 + e3 + e4 + avisos


def validar_bateria(telemetrias, config):
    inconsistencias = []
    for r in telemetrias:
        esperado = r["bateria_kwh"] / config["capacidade_total_bateria_kwh"] * 100
        r["bateria_pct_validado"] = r["bateria_pct"]
        if abs(esperado - r["bateria_pct"]) > config["tolerancia_bateria_pct"]:
            r["bateria_pct_validado"] = max(0, min(100, esperado))
            inconsistencias.append({
                "horario": r["horario"],
                "campo": "bateria_pct",
                "valor_informado": r["bateria_pct"],
                "valor_esperado": esperado,
                "descricao": "Inconsistência detectada: percentual da bateria divergente da carga em kWh.",
            })
    return inconsistencias


def validar_consumo_antes_mitigacao(registro, consumo_nominal, config):
    diferenca = abs(registro["consumo_medido_kwh"] - consumo_nominal)
    if diferenca > config["tolerancia_consumo_kwh"]:
        return {
            "horario": registro["horario"],
            "campo": "consumo_medido_kwh",
            "valor_informado": registro["consumo_medido_kwh"],
            "valor_esperado": consumo_nominal,
            "descricao": "Consumo medido difere do consumo nominal antes das mitigações.",
        }
    return None



# MODEL -- ESTRUTURAS DE DADOS


def criar_hierarquia_colonia(modulos):
    return {
        "energia": {"solar": "paineis_solares", "eolica": "turbinas_eolicas", "baterias": "banco_baterias"},
        "suporte_vida": {n: modulos[n] for n in ("habitacao", "alimentacao", "suporte_medico")},
        "operacao": {n: modulos[n] for n in ("centro_logistico", "laboratorio")},
    }


def criar_matriz_telemetria(telemetrias):
    colunas = ["horario", "solar_kwh", "eolica_kwh", "bateria_pct_validado", "consumo_medido_kwh", "radiacao_msv", "pressao_kpa", "vento_kmh"]
    return colunas, [[r[c] for c in colunas] for r in telemetrias]


def extrair_historico(telemetrias):
    return {
        "bateria": [r["bateria_pct_validado"] for r in telemetrias],
        "solar": [r["solar_kwh"] for r in telemetrias],
        "eolica": [r["eolica_kwh"] for r in telemetrias],
        "consumo": [r["consumo_medido_kwh"] for r in telemetrias],
    }



# CONTROLLER -- REGRAS AMBIENTAIS


def enfileirar_alerta(fila, severidade, origem, horario, mensagem, recomendacao, acao=""):
    alerta = {
        "severidade": severidade,
        "prioridade": PRIORIDADE_ALERTA.get(severidade, 3),
        "origem": origem,
        "horario": horario,
        "mensagem": mensagem,
        "recomendacao": recomendacao,
        "acao_executada": acao,
    }
    chave = (severidade, origem, horario, mensagem)
    if chave not in {(a["severidade"], a["origem"], a["horario"], a["mensagem"]) for a in fila}:
        fila.append(alerta)
    return alerta


def ordenar_fila_alertas(fila):
    return sorted(fila, key=lambda a: (a["prioridade"], a["horario"], a["origem"]))


def registrar_evento_critico(pilha, evento):
    if evento.get("severidade") == "critico":
        pilha.append(evento)


def sincronizar_criticos(fila, pilha):
    vistos = {(e.get("horario"), e.get("origem", e.get("modulo")), e.get("mensagem", e.get("descricao"))) for e in pilha}
    for alerta in fila:
        chave = (alerta["horario"], alerta["origem"], alerta["mensagem"])
        if alerta["severidade"] == "critico" and chave not in vistos:
            pilha.append(alerta)
            vistos.add(chave)


def analisar_temperatura_interna(r, fila):
    v = r["temperatura_interna_c"]
    if v < 16:
        enfileirar_alerta(fila, "critico", "ambiente", r["horario"], "Temperatura interna crítica por frio.", "Redirecionar energia aos aquecedores.")
        return "critico"
    elif v > 27:
        enfileirar_alerta(fila, "critico", "ambiente", r["horario"], "Temperatura interna crítica por calor.", "Redirecionar energia ao resfriamento.")
        return "critico"
    elif v < 18 or v > 24:
        enfileirar_alerta(fila, "alerta", "ambiente", r["horario"], "Anomalia térmica interna.", "Ajustar controle térmico.")
        return "alerta"
    return "normal"


def analisar_temperatura_externa(r, fila):
    v = r["temperatura_externa_c"]
    if v < -75 or v > -15:
        enfileirar_alerta(fila, "critico", "ambiente", r["horario"], "Temperatura externa crítica.", "Proteger componentes externos.")
        return "critico"
    elif v < -70 or v > -20:
        enfileirar_alerta(fila, "alerta", "ambiente", r["horario"], "Temperatura externa anômala.", "Monitorar estruturas externas.")
        return "alerta"
    return "normal"


def analisar_radiacao(r, fila):
    if r["radiacao_msv"] > 0.50:
        enfileirar_alerta(fila, "critico", "ambiente", r["horario"], "Radiação crítica.", "Guiar colonos aos abrigos.")
        return "critico"
    elif r["radiacao_msv"] > 0.30:
        enfileirar_alerta(fila, "alerta", "ambiente", r["horario"], "Radiação acima do normal.", "Limitar atividades externas.")
        return "alerta"
    return "normal"


def analisar_pressao(r, fila):
    if r["pressao_kpa"] < 300 or r["pressao_kpa"] > 450:
        enfileirar_alerta(fila, "critico", "ambiente", r["horario"], "Pressão crítica.", "Isolar área afetada.")
        return "critico"
    elif r["pressao_kpa"] < 350 or r["pressao_kpa"] > 400:
        enfileirar_alerta(fila, "alerta", "ambiente", r["horario"], "Pressão fora da faixa ideal.", "Regular válvulas.")
        return "alerta"
    return "normal"


def analisar_vento(r, fila, acoes):
    if r["vento_kmh"] > 160:
        acao = "Travamento mecânico das turbinas acionado."
        enfileirar_alerta(fila, "critico", "energia", r["horario"], "Travamento mecânico das turbinas.", "Manter turbinas travadas.", acao)
        acoes.append({"horario": r["horario"], "acao": acao})
        return 0, True
    elif r["vento_kmh"] >= 100:
        enfileirar_alerta(fila, "alerta", "energia", r["horario"], "Tempestade de poeira severa.", "Preparar manutenção por abrasão.")
    elif 10 <= r["vento_kmh"] <= 20:
        enfileirar_alerta(fila, "normal", "energia", r["horario"], "Geração eólica baixa.", "Usar excedente solar para baterias.")
    return r["eolica_kwh"], False


def analisar_sensores(r, fila, acoes):
    if r["sensores_funcionais"] != 1:
        acao = "Automações de pouso e decolagem bloqueadas."
        enfileirar_alerta(fila, "critico", "sensores", r["horario"], "Sensores inseguros.", "Inspecionar sensores manualmente.", acao)
        acoes.append({"horario": r["horario"], "acao": acao})
        return True
    return False


def analisar_comunicacao(r, config, fila):
    q = r["qualidade_comunicacao_pct"]
    if q < config["limite_comunicacao_critico_pct"]:
        enfileirar_alerta(fila, "critico", "comunicação", r["horario"], "Comunicação crítica.", "Ativar canal de emergência.")
        return "critico"
    elif q < config["limite_comunicacao_alerta_pct"]:
        enfileirar_alerta(fila, "alerta", "comunicação", r["horario"], "Comunicação degradada.", "Priorizar telemetria essencial.")
        return "alerta"
    return "normal"


def analisar_bateria_atual(registro, config, fila):
    percentual = registro["bateria_pct_validado"]
    if percentual < config["limite_bateria_critico_pct"]:
        enfileirar_alerta(
            fila,
            "critico",
            "energia",
            registro["horario"],
            f"Reserva de bateria em nível crítico: {percentual:.1f}%.",
            "Preservar suporte vital e reduzir consumo não essencial.",
        )
        return "critico"
    if percentual < config["limite_bateria_alerta_pct"]:
        enfileirar_alerta(
            fila,
            "alerta",
            "energia",
            registro["horario"],
            f"Reserva de bateria baixa: {percentual:.1f}%.",
            "Ativar modo de economia.",
        )
        return "alerta"
    return "normal"


def analisar_ambiente(registro, config, fila, acoes):
    eolica, travada = analisar_vento(registro, fila, acoes)
    return {
        "temperatura_interna": analisar_temperatura_interna(registro, fila),
        "temperatura_externa": analisar_temperatura_externa(registro, fila),
        "radiacao": analisar_radiacao(registro, fila),
        "pressao": analisar_pressao(registro, fila),
        "comunicacao": analisar_comunicacao(registro, config, fila),
        "eolica_efetiva": eolica,
        "turbinas_travadas": travada,
        "sensores_inseguros": analisar_sensores(registro, fila, acoes),
    }



# CONTROLLER -- ENERGIA, MITIGAÇÕES E ALERTAS


def consumo_nominal(modulos):
    return sum(m["consumo_nominal_kwh"] for m in modulos.values() if m["estado_binario"] == 1)


def consumo_atual(modulos):
    return sum(m["consumo_atual_kwh"] for m in modulos.values() if m["estado_binario"] == 1)


def energia_disponivel(registro, eolica_efetiva):
    return registro["solar_kwh"] + eolica_efetiva + registro["bateria_kwh"]


def rotulo_modulo(nome):
    rotulos = {
        "habitacao": "habitação",
        "alimentacao": "alimentação",
        "suporte_medico": "suporte médico",
        "centro_logistico": "centro logístico",
        "energia": "energia",
        "laboratorio": "laboratório",
    }
    return rotulos.get(nome, nome)


def analisar_modulos(modulos, fila):
    for modulo in modulos.values():
        if modulo["estado_binario"] == 0:
            nome = rotulo_modulo(modulo["nome"])
            if modulo["nome"] in PROTEGIDOS:
                severidade = "critico"
                recomendacao = "Priorizar manutenção imediata e preservar suporte vital."
            else:
                severidade = "alerta"
                recomendacao = "Programar manutenção do módulo."
            enfileirar_alerta(fila, severidade, "módulos", "atual", f"Falha detectada no módulo {nome}.", recomendacao)


def reduzir_modulo(modulo, percentual, horario, fila, acoes, motivo, emergencial=False):
    antes = modulo["consumo_atual_kwh"]
    modulo["consumo_atual_kwh"] = modulo["consumo_nominal_kwh"] * (1 - percentual / 100)
    modulo["status_operacional"] = "reduzido"
    modulo["percentual_reducao"] = percentual
    modulo["motivo_alteracao"] = motivo
    tipo = "Redução emergencial" if emergencial else "Redução parcial"
    acao = f"{tipo} do módulo {rotulo_modulo(modulo['nome'])}: {percentual:.0f}%."
    acoes.append({"horario": horario, "acao": acao})
    enfileirar_alerta(fila, "alerta", "energia", horario, f"{tipo} aplicada em {rotulo_modulo(modulo['nome'])}.", motivo, acao)
    return antes - modulo["consumo_atual_kwh"]


def desligar_modulo(modulo, horario, fila, acoes, motivo):
    economia = modulo["consumo_atual_kwh"]
    modulo["consumo_atual_kwh"] = 0
    modulo["status_operacional"] = "desligado"
    modulo["percentual_reducao"] = 100
    modulo["motivo_alteracao"] = motivo
    acao = f"Módulo {rotulo_modulo(modulo['nome'])} desligado completamente."
    acoes.append({"horario": horario, "acao": acao})
    enfileirar_alerta(fila, "alerta", "energia", horario, f"Desligamento aplicado em {rotulo_modulo(modulo['nome'])}.", motivo, acao)
    return economia


def aplicar_mitigacoes(modulos, deficit, config, horario, fila, acoes, preventivo=False):
    if deficit <= 0 and not preventivo:
        return deficit
    sequencia = [
        ("laboratorio", "desligar", 100),
        ("energia", "reduzir", config["percentual_reducao_energia"]),
        ("centro_logistico", "reduzir", config["percentual_reducao_centro_logistico"]),
        ("centro_logistico", "desligar", 100),
        ("alimentacao", "reduzir_emergencial", config["percentual_reducao_alimentacao"]),
    ]
    for nome, tipo, percentual in sequencia:
        if deficit <= 0 and not preventivo:
            break
        modulo = modulos[nome]
        if nome in PROTEGIDOS:
            continue
        if tipo == "desligar" and modulo["pode_desligar"] != 1:
            continue
        if tipo == "desligar" and modulo["status_operacional"] != "desligado":
            deficit -= desligar_modulo(modulo, horario, fila, acoes, f"{rotulo_modulo(nome)} tem baixa prioridade no corte.")
        elif tipo == "reduzir" and modulo["status_operacional"] == "ativo":
            deficit -= reduzir_modulo(modulo, percentual, horario, fila, acoes, "Funções críticas preservadas.")
        elif tipo == "reduzir_emergencial" and modulo["status_operacional"] == "ativo":
            deficit -= reduzir_modulo(modulo, percentual, horario, fila, acoes, "Usado somente em último caso.", True)
        if preventivo and nome == "laboratorio":
            break
    if deficit > 0 and not preventivo:
        enfileirar_alerta(fila, "critico", "energia", horario, f"Déficit remanescente de {deficit:.1f} kWh.", "Manter suporte vital e solicitar decisão humana.")
    return deficit


def analisar_abrasao_turbinas(telemetrias, ciclo_horas, fila, acoes):
    seguidos = maior = 0
    horario_maior = ""
    travou_atual = travou_maior = False
    for r in telemetrias:
        if r["vento_kmh"] >= 100:
            seguidos += 1
            travou_atual = travou_atual or r["vento_kmh"] > 160
            if seguidos > maior:
                maior, horario_maior, travou_maior = seguidos, r["horario"], travou_atual
        else:
            seguidos = 0
            travou_atual = False
    duracao = maior * ciclo_horas
    if duracao > 6:
        severidade = "critico" if travou_maior else "alerta"
        msg = f"Abrasão prolongada nas turbinas: vento acima de 100 km/h por {duracao:.0f} horas."
        enfileirar_alerta(fila, severidade, "energia", horario_maior, msg, "Programar manutenção preventiva.")
        acoes.append({"horario": horario_maior, "acao": f"Manutenção preventiva registrada após {duracao:.0f} horas de vento severo."})
    return duracao


def registrar_travamentos_historicos(telemetrias, fila, acoes):
    for r in telemetrias[:-1]:
        if r["vento_kmh"] > 160:
            analisar_vento(r, fila, acoes)


def status_modulo(modulo, contexto):
    if modulo["estado_binario"] == 0:
        return "critico"
    if modulo["nome"] == "energia" and contexto["deficit_final"] > contexto["config"]["tolerancia_consumo_kwh"]:
        return "critico"
    if modulo["status_operacional"] in ("reduzido", "desligado"):
        return "alerta"
    return "normal"



# CONTROLLER -- PREVISÃO POR REGRESSÃO LINEAR


def media(valores):
    return sum(valores) / len(valores) if valores else 0


def regressao_linear(x, y):
    if len(x) < 2 or len(x) != len(y):
        return None
    mx, my = media(x), media(y)
    den = sum((xi - mx) ** 2 for xi in x)
    if den == 0:
        return None
    a = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / den
    return a, my - a * mx


def r2(x, y, a, b):
    my = media(y)
    total = sum((yi - my) ** 2 for yi in y)
    if total == 0:
        return 0
    residuos = sum((yi - (a * xi + b)) ** 2 for xi, yi in zip(x, y))
    return 1 - residuos / total


def prever_bateria(historico):
    x = list(range(1, len(historico) + 1))
    modelo = regressao_linear(x, historico)
    if modelo is None:
        return {"historico": historico, "inclinacao": 0, "intercepto": 0, "r2": 0, "previsao": None, "interpretacao": "Histórico insuficiente."}
    a, b = modelo
    previsto = max(0, min(100, a * (len(historico) + 1) + b))
    if a < -5:
        texto = "Tendência de queda forte."
    elif a < 0:
        texto = "Tendência de queda moderada."
    else:
        texto = "Reserva estável ou em recuperação."
    return {"historico": historico, "inclinacao": a, "intercepto": b, "r2": r2(x, historico, a, b), "previsao": previsto, "interpretacao": texto}


def aplicar_decisao_previsao(previsao, config, modulos, fila, acoes, horario):
    valor = previsao["previsao"]
    if valor is None:
        enfileirar_alerta(fila, "alerta", "previsão", horario, "Previsão indisponível.", "Coletar mais ciclos.")
        return "Sem decisão automática."
    if valor < config["limite_previsao_critico_pct"]:
        enfileirar_alerta(fila, "critico", "previsão", horario, f"Previsão crítica de bateria: {valor:.1f}%.", "Aplicar corte preventivo.")
        aplicar_mitigacoes(modulos, 1, config, horario, fila, acoes, preventivo=True)
        return "Corte preventivo influenciado pela regressão."
    elif valor < config["limite_previsao_alerta_pct"]:
        acao = "Modo de economia ativado pela previsão."
        enfileirar_alerta(fila, "alerta", "previsão", horario, f"Previsão baixa de bateria: {valor:.1f}%.", "Ativar economia.", acao)
        acoes.append({"horario": horario, "acao": acao})
        return "Modo de economia ativado."
    enfileirar_alerta(fila, "normal", "previsão", horario, f"Previsão controlada: {valor:.1f}%.", "Manter monitoramento.")
    return "Sem corte preventivo."



# VIEW -- EXIBIÇÃO DO RELATÓRIO NO TERMINAL


def texto_status(valor, maiusculo=False):
    mapa = {"critico": "crítico", "alerta": "alerta", "normal": "normal", "informativo": "informativo"}
    texto = mapa.get(str(valor).lower(), str(valor))
    return texto.upper() if maiusculo else texto


def mostrar_lista(titulo, itens):
    print(f"\n{titulo}")
    if not itens:
        print("- Nenhum registro.")
    for item in itens:
        print(f"- {item}")


def exibir_relatorio_final(c):
    r = c["registro_atual"]
    print("=" * 60)
    print("SISTEMA AURORA - MONITORAMENTO OPERACIONAL DA COLÔNIA")
    print("=" * 60)
    print("\nCICLO ANALISADO")
    print(f"- Horário final: {r['horario']} | ciclo: {c['config']['ciclo_horas']:.0f} horas")
    print("\nSTATUS GERAL")
    print(f"- {texto_status(c['status_geral'], True)}")

    print("\n1. STATUS DOS MÓDULOS")
    print("Módulo            | status  | operação")
    for m in sorted(c["modulos"].values(), key=lambda x: x["prioridade"]):
        print(f"{rotulo_modulo(m['nome']):<17} | {texto_status(status_modulo(m, c)):<7} | {m['status_operacional']}")

    print("\n2. CONDIÇÕES OPERACIONAIS E AMBIENTAIS")
    a = c["ambiente"]
    print(f"- Temperatura interna/externa: {texto_status(a['temperatura_interna'])} / {texto_status(a['temperatura_externa'])}")
    print(f"- Radiação: {texto_status(a['radiacao'])} | Pressão: {texto_status(a['pressao'])} | Comunicação: {texto_status(a['comunicacao'])}")
    print(f"- Vento: {r['vento_kmh']:.1f} km/h | eólica efetiva: {a['eolica_efetiva']:.1f} kWh")
    print(f"- Bateria atual: {r['bateria_pct_validado']:.1f}% | status: {texto_status(c['status_bateria'])}")
    print(f"- Automações de pouso e decolagem: {'BLOQUEADAS' if a['sensores_inseguros'] else 'LIBERADAS'}")

    print("\n3. BALANÇO ENERGÉTICO")
    print(f"- Consumo medido pela telemetria: {r['consumo_medido_kwh']:.1f} kWh")
    print(f"- Consumo nominal dos módulos: {c['consumo_nominal']:.1f} kWh")
    print(f"- Consumo atual após mitigação: {c['consumo_atual']:.1f} kWh")
    print(f"- Diferença após medidas de mitigação: {abs(r['consumo_medido_kwh'] - c['consumo_atual']):.1f} kWh")
    print(f"- Energia disponível: {c['energia_disponivel']:.1f} kWh | déficit: {max(0, c['deficit_final']):.1f} kWh")

    print("\n4. HIERARQUIA DA COLÔNIA")
    print("COLÔNIA\n|-- ENERGIA\n|   |-- Solar\n|   |-- Eólica\n|   `-- Baterias\n|-- SUPORTE DE VIDA\n|   |-- Habitação\n|   |-- Alimentação\n|   `-- Suporte médico\n`-- OPERAÇÃO\n    |-- Centro logístico\n    `-- Laboratório")

    print("\n5. MATRIZ DE TELEMETRIA")
    print(" | ".join(c["colunas_matriz"]))
    for linha in c["matriz_telemetria"]:
        print(" | ".join(f"{v:.2f}" if isinstance(v, float) else str(v) for v in linha))

    print("\n6. INCONSISTÊNCIAS DETECTADAS")
    if not c["inconsistencias"]:
        print("- Nenhuma inconsistência detectada.")
    for i in c["inconsistencias"]:
        esperado = f"{i['valor_esperado']:.1f}" if isinstance(i["valor_esperado"], float) else i["valor_esperado"]
        print(f"- {i['horario']} {i['campo']}: informado {i['valor_informado']}, esperado {esperado}. {i['descricao']}")

    p = c["previsao"]
    print("\n7. PREVISÃO DA BATERIA")
    print(f"- Histórico: {', '.join(f'{v:.1f}%' for v in p['historico'])}")
    print(f"- Inclinação: {p['inclinacao']:.4f} | intercepto: {p['intercepto']:.4f} | R2: {p['r2']:.4f}")
    if p["previsao"] is None:
        print(f"- Próximo ciclo: indisponível | decisão: {c['decisao_previsao']}")
    else:
        print(f"- Próximo ciclo: {p['previsao']:.1f}% | decisão: {c['decisao_previsao']}")

    print("\n8. ALERTAS, RECOMENDAÇÕES E EVENTOS CRÍTICOS")
    for alerta in c["alertas"]:
        print(f"- [{texto_status(alerta['severidade'], True)}] {alerta['horario']} {alerta['origem']}: {alerta['mensagem']} Recom.: {alerta['recomendacao']}")
    print("  Eventos críticos recentes:")
    for e in reversed(c["pilha_eventos"][-5:]):
        print(f"  - {e.get('horario')} {e.get('origem', e.get('modulo'))}: {e.get('mensagem', e.get('descricao'))}")

    mostrar_lista("\n9. AÇÕES AUTOMÁTICAS EXECUTADAS", [f"{a['horario']}: {a['acao']}" for a in c["acoes"]])



# MAIN -- FLUXO PRINCIPAL


def preparar_contexto(caminho=None):
    config, modulos, telemetrias, eventos, erros = carregar_dados(caminho)
    fila, pilha, acoes = [], [], []
    analisar_modulos(modulos, fila)
    for erro in erros:
        enfileirar_alerta(fila, "alerta", "validação", "arquivo", erro, "Corrigir data/dados.txt.")
    for evento in eventos:
        registrar_evento_critico(pilha, evento)

    inconsistencias = validar_bateria(telemetrias, config)
    registro = telemetrias[-1]
    status_bateria = analisar_bateria_atual(registro, config, fila)
    consumo_base = consumo_nominal(modulos)
    consumo_inicial = validar_consumo_antes_mitigacao(registro, consumo_base, config)
    if consumo_inicial:
        inconsistencias.append(consumo_inicial)
    for item in inconsistencias:
        enfileirar_alerta(fila, "alerta", "validação", item["horario"], f"Inconsistência em {item['campo']}.", "Usar valor corrigido na análise.")

    registrar_travamentos_historicos(telemetrias, fila, acoes)
    duracao_abrasao = analisar_abrasao_turbinas(telemetrias, config["ciclo_horas"], fila, acoes)
    ambiente = analisar_ambiente(registro, config, fila, acoes)
    disponivel = energia_disponivel(registro, ambiente["eolica_efetiva"])

    historico = extrair_historico(telemetrias)
    previsao = prever_bateria(historico["bateria"])
    decisao = aplicar_decisao_previsao(previsao, config, modulos, fila, acoes, registro["horario"])

    deficit = consumo_atual(modulos) - disponivel
    aplicar_mitigacoes(modulos, deficit, config, registro["horario"], fila, acoes)
    atual = consumo_atual(modulos)
    deficit_final = atual - disponivel
    bateria_baixa = status_bateria in ("alerta", "critico")
    crise = ambiente["sensores_inseguros"] or ambiente["radiacao"] == "critico" or ambiente["pressao"] == "critico" or (deficit_final > 0 and bateria_baixa)
    sincronizar_criticos(fila, pilha)
    colunas, matriz = criar_matriz_telemetria(telemetrias)

    return {
        "config": config,
        "modulos": modulos,
        "registro_atual": registro,
        "ambiente": ambiente,
        "status_bateria": status_bateria,
        "hierarquia": criar_hierarquia_colonia(modulos),
        "historico": historico,
        "colunas_matriz": colunas,
        "matriz_telemetria": matriz,
        "inconsistencias": inconsistencias,
        "consumo_nominal": consumo_base,
        "consumo_atual": atual,
        "energia_disponivel": disponivel,
        "deficit_final": deficit_final,
        "previsao": previsao,
        "decisao_previsao": decisao,
        "duracao_abrasao": duracao_abrasao,
        "alertas": ordenar_fila_alertas(fila),
        "pilha_eventos": pilha,
        "acoes": acoes,
        "status_geral": "CRITICO" if crise or any(a["severidade"] == "critico" for a in fila) else ("ALERTA" if any(a["severidade"] == "alerta" for a in fila) else "NORMAL"),
    }


def main():
    try:
        contexto = preparar_contexto()
        exibir_relatorio_final(contexto)
    except (FileNotFoundError, ValueError) as erro:
        print("Erro ao executar o Sistema Aurora:")
        print(erro)


if __name__ == "__main__":
    main()
