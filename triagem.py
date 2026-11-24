"""Geração sintética e inferência conservadora para a triagem de extratos."""

import argparse
from bisect import bisect_left, bisect_right
import csv
from itertools import chain
import json
from math import exp, isfinite
from pathlib import Path
from random import Random

CAMADAS = ("ccd", "fenois", "dpph", "fps", "uv")
COLUNAS = ("id", *CAMADAS, "dna", "viavel")
PADRAO = Path(__file__).with_name("parametros.json")
CONTINUIDADE = "continuidade"


def configurar(caminho=PADRAO):
    cfg = json.loads(Path(caminho).read_text(encoding="utf-8"))
    for campo, quantidade in (("ccd_cortes", 2), ("fenois", 2), ("dpph", 4),
                              ("fps", 4), ("uv", 2)):
        cortes = (cfg["simulacao"]["ccd_cortes"] if campo == "ccd_cortes"
                  else cfg["cortes"][campo])
        if len(cortes) != quantidade or not all(map(isfinite, cortes)) or sorted(set(cortes)) != cortes:
            raise ValueError(f"Cortes inválidos para {campo}")
    if len(cfg["ccd"]) != 3 or len(set(cfg["ccd"])) != 3:
        raise ValueError("CCD deve ter três categorias distintas")
    if not 0 <= cfg["corte_dna"] <= 1:
        raise ValueError("O corte de DNA deve estar entre 0 e 1")
    return cfg


def gerar_base(cfg, rng, tamanho, prefixo):
    sim = cfg["simulacao"]
    for indice in range(1, tamanho + 1):
        potencial = rng.gauss(0, 1)

        def leitura(campo):
            media, coeficiente, ruido = sim[campo]
            return media + coeficiente * potencial + rng.gauss(0, ruido)

        perfil = leitura("ccd")
        fenois = max(0, leitura("fenois"))
        dpph = exp(leitura("log_dpph"))
        fps = exp(leitura("log_fps"))
        uv = leitura("uv")
        if rng.random() < sim["prob_falha_uv"]:
            uv -= sim["perda_uv"]
        uv = round(min(1, max(0, uv)), 6)
        dna = leitura("dna") + sim["peso_uv_no_dna"] * uv
        if rng.random() < sim["prob_falha_dna"]:
            dna -= sim["perda_dna"]
        dna = round(min(1, max(0, dna)), 6)
        yield {
            "id": f"{prefixo}-{indice:06d}",
            "ccd": cfg["ccd"][bisect_right(sim["ccd_cortes"], perfil)],
            "fenois": round(fenois, 6),
            "dpph": round(dpph, 6),
            "fps": round(fps, 6),
            "uv": uv,
            "dna": dna,
            "viavel": int(dna >= cfg["corte_dna"]),
        }


def gerar(cfg, semente=42, n_treino=2000, n_teste=500):
    if min(n_treino, n_teste) < 1:
        raise ValueError("Os tamanhos das bases devem ser positivos")
    sementes = Random(semente)
    rng_treino = Random(sementes.getrandbits(128))
    rng_teste = Random(sementes.getrandbits(128))
    return (list(gerar_base(cfg, rng_treino, n_treino, "treino")),
            list(gerar_base(cfg, rng_teste, n_teste, "teste")))


def escrever_csv(caminho, colunas, linhas):
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(linhas)


def ler_csv(caminho, cfg):
    ids = set()
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        if not set(COLUNAS).issubset(leitor.fieldnames or ()):
            raise ValueError(f"{caminho}: colunas obrigatórias: {', '.join(COLUNAS)}")
        for linha in leitor:
            try:
                amostra = {campo: linha[campo].strip() for campo in COLUNAS}
                for campo in (*CAMADAS[1:], "dna"):
                    valor = float(amostra[campo])
                    if not isfinite(valor) or valor < 0:
                        raise ValueError(f"{campo} deve ser finito e não negativo")
                    amostra[campo] = valor
                amostra["viavel"] = int(amostra["viavel"])
                if amostra["viavel"] != int(amostra["dna"] >= cfg["corte_dna"]):
                    raise ValueError("viavel diverge do corte de DNA")
                if max(amostra["uv"], amostra["dna"]) > 1:
                    raise ValueError("UV e DNA devem estar entre 0 e 1")
                if amostra["ccd"] not in cfg["ccd"]:
                    raise ValueError("categoria CCD desconhecida")
                if not amostra["id"] or amostra["id"] in ids:
                    raise ValueError("ID ausente ou duplicado")
            except (AttributeError, ValueError) as erro:
                raise ValueError(f"{caminho}, linha {leitor.line_num}: {erro}") from erro
            ids.add(amostra["id"])
            yield amostra
        if not ids:
            raise ValueError(f"{caminho}: nenhuma amostra")


def alfabeto(cfg, niveis):
    if niveis not in (3, 5):
        raise ValueError("Escolha 3 ou 5 níveis")
    return [tuple(f"{campo}:{i}" for i in range(1, 1 + quantidade))
            for campo, quantidade in zip(CAMADAS, (len(cfg["ccd"]), 3, niveis, niveis, 3))]


def discretizar(amostra, cfg, niveis):
    grupos = alfabeto(cfg, niveis)
    indices = [cfg["ccd"].index(amostra["ccd"])]
    for campo in CAMADAS[1:]:
        cortes = cfg["cortes"][campo]
        valor = amostra[campo]
        indice = bisect_right(cortes, valor)
        # Os limites superiores de fenóis médio e DPPH baixo são inclusivos.
        if campo in ("fenois", "dpph") and valor == cortes[-1]:
            indice = bisect_left(cortes, valor)
        if niveis == 3 and campo in ("dpph", "fps"):
            indice = (0, 0, 1, 2, 2)[indice]
        indices.append(indice)
    return tuple(grupo[indice] for grupo, indice in zip(grupos, indices))


def treinar(rastros, grupos, kmin=3, *, fundir=True):
    if kmin < 1:
        raise ValueError("kmin deve ser positivo")
    simbolos = list(chain.from_iterable(grupos))
    contagens = {(): [0, 0]}
    for rastro, viavel in rastros:
        rastro = tuple(rastro)
        if viavel not in (0, 1) or len(rastro) != len(grupos) or any(
            s not in grupo for s, grupo in zip(rastro, grupos)
        ):
            raise ValueError("Rastro ou rótulo inválido")
        for camada in range(len(rastro) + 1):
            contagens.setdefault(rastro[:camada], [0, 0])[viavel] += 1

    estados = {CONTINUIDADE: {"camada": None, "prefixos": 0, "inviaveis": 0, "viaveis": 0}}
    saidas = {CONTINUIDADE: "AVANCAR"}
    transicoes = {CONTINUIDADE: dict.fromkeys(simbolos, CONTINUIDADE)}
    representantes = {}
    equivalentes = {}
    for prefixo in sorted(contagens, key=lambda p: (-len(p), p)):
        camada = len(prefixo)
        inviaveis, viaveis = contagens[prefixo]
        descartar = camada in (4, 5) and inviaveis >= kmin and not viaveis
        saida = "DESCARTAR" if descartar else "AVANCAR"
        # Preserva as classes pura inviável, pura viável, mista e sem evidência.
        evidencia = (bool(inviaveis), bool(viaveis))
        destinos = {s: representantes.get(prefixo + (s,), CONTINUIDADE) for s in simbolos}
        assinatura = (camada, saida, evidencia, tuple(destinos.values()))
        estado = equivalentes.get(assinatura) if fundir else None
        if estado is None:
            estado = f"q{len(estados) - 1}"
            equivalentes[assinatura] = estado
            estados[estado] = {"camada": camada, "prefixos": 0, "inviaveis": 0, "viaveis": 0}
            saidas[estado] = saida
            transicoes[estado] = destinos
        representantes[prefixo] = estado
        estados[estado]["prefixos"] += 1
        estados[estado]["inviaveis"] += inviaveis
        estados[estado]["viaveis"] += viaveis

    return {
        "alfabeto": simbolos, "alfabeto_saida": ["AVANCAR", "DESCARTAR"],
        "inicial": representantes[()], "estados": estados,
        "transicoes": transicoes, "saidas": saidas,
        "estados_antes": len(contagens) + 1, "estados_depois": len(estados),
        "kmin": kmin,
    }


def percurso(modelo, rastro):
    estado = modelo["inicial"]
    yield estado
    for simbolo in rastro:
        estado = modelo["transicoes"][estado][simbolo]
        yield estado


def avaliar(modelo, amostras):
    for amostra in amostras:
        rastro = discretizar(amostra, modelo["configuracao"], modelo["niveis"])
        descarte = next((camada for camada, estado in enumerate(percurso(modelo, rastro))
                         if modelo["saidas"][estado] == "DESCARTAR"), None)
        yield {"id": amostra["id"], "decisao": "DESCARTAR" if descarte else "AVANCAR",
               "camada_descarte": descarte, "viavel": amostra["viavel"],
               "falso_descarte": int(descarte is not None and amostra["viavel"] == 1)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    geracao = comandos.add_parser("gerar")
    geracao.add_argument("--config", type=Path, default=PADRAO)
    geracao.add_argument("--semente", type=int, default=42)
    geracao.add_argument("--n-treino", type=int, default=2000)
    geracao.add_argument("--n-teste", type=int, default=500)
    geracao.add_argument("--treino", type=Path, default=Path("exemplo_treino.csv"))
    geracao.add_argument("--teste", type=Path, default=Path("exemplo_teste.csv"))
    treino = comandos.add_parser("treinar")
    treino.add_argument("csv", type=Path)
    treino.add_argument("--config", type=Path, default=PADRAO)
    treino.add_argument("--niveis", type=int, choices=(3, 5), default=3)
    treino.add_argument("--kmin", type=int, default=3)
    treino.add_argument("--saida", type=Path, default=Path("moore.json"))
    teste = comandos.add_parser("avaliar")
    teste.add_argument("modelo", type=Path)
    teste.add_argument("csv", type=Path)
    teste.add_argument("--saida", type=Path, default=Path("decisoes.csv"))
    args = parser.parse_args()
    try:
        if args.comando == "gerar":
            caminhos = {p.resolve() for p in (args.treino, args.teste, args.config)}
            if len(caminhos) != 3:
                raise ValueError("Escolha caminhos distintos para configuração, treino e teste")
            bases = gerar(configurar(args.config), args.semente, args.n_treino, args.n_teste)
            for caminho, base in zip((args.treino, args.teste), bases):
                escrever_csv(caminho, COLUNAS, base)
                print(f"{caminho}: {len(base)} amostras")
        elif args.comando == "treinar":
            if args.saida.resolve() in (args.csv.resolve(), args.config.resolve()):
                raise ValueError("A saída deve ser diferente dos arquivos de entrada")
            cfg = configurar(args.config)
            rastros = ((discretizar(a, cfg, args.niveis), a["viavel"])
                       for a in ler_csv(args.csv, cfg))
            modelo = treinar(rastros, alfabeto(cfg, args.niveis), args.kmin)
            modelo.update(configuracao=cfg, niveis=args.niveis)
            args.saida.write_text(json.dumps(modelo, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
            print(f"Estados: {modelo['estados_antes']} → {modelo['estados_depois']}")
        else:
            if args.saida.resolve() in (args.csv.resolve(), args.modelo.resolve()):
                raise ValueError("A saída deve ser diferente dos arquivos de entrada")
            modelo = json.loads(args.modelo.read_text(encoding="utf-8"))
            resultados = list(avaliar(modelo, ler_csv(args.csv, modelo["configuracao"])))
            escrever_csv(args.saida, tuple(resultados[0]), resultados)
            viaveis = sum(r["viavel"] for r in resultados)
            falsos = sum(r["falso_descarte"] for r in resultados)
            taxa = f"{falsos / viaveis:.2%}" if viaveis else "indefinida"
            descartes = sum(r["decisao"] == "DESCARTAR" for r in resultados)
            print(f"{len(resultados)} amostras, {descartes} descartes, "
                  f"{falsos}/{viaveis} falsos descartes ({taxa})")
    except (OSError, ValueError, KeyError, TypeError) as erro:
        parser.exit(2, f"Erro: {erro}\n")


if __name__ == "__main__":
    main()
