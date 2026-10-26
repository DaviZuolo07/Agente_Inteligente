"""Monta os dados derivados das provas oficiais que entram na base do Tutor ENEM.

1. dados/banco_questoes_enem.json — questões de questoes_extraidas.json (saída de extrair_questoes.py) que:
   - pertencem a uma matéria com tutor (classificacao_questoes.csv: Física, Biologia, História, Geografia, Matemática);
   - foram extraídas por completo (5 alternativas em texto + gabarito oficial) e não foram anuladas.
   Química, Filosofia e Sociologia ficam de fora porque não há tutor dessas disciplinas.
2. docs/proposta_redacao_enem{ano}.md — proposta de redação (tema + textos motivadores) de cada ano,
   com <!-- pagina: N --> apontando para a página do caderno oficial.

Uso: python montar_banco.py <questoes_extraidas.json> <classificacao_questoes.csv> <pasta_docs> <pasta_dados>
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import fitz

EXTRAIDAS, CLASSIFICACAO, DOCS, DADOS = map(Path, sys.argv[1:5])

classe = {linha["id"]: linha for linha in csv.DictReader(CLASSIFICACAO.open(encoding="utf-8"))}
banco, descartes = [], Counter()
for q in json.loads(EXTRAIDAS.read_text(encoding="utf-8")):
    c = classe[q["id"]]
    if not c["materia_tutor"]:
        descartes[f"sem tutor ({c['disciplina']})"] += 1
        continue
    if q["anulada"]:
        descartes["anulada pelo INEP"] += 1
        continue
    if not q["extracao_ok"]:
        descartes["alternativas em figura"] += 1
        continue
    banco.append({k: q[k] for k in ("id", "ano", "dia", "numero", "enunciado", "alternativas", "gabarito",
                                    "anulada", "pagina", "fonte_arquivo", "tem_imagem")}
                 | {"materia": c["materia_tutor"], "disciplina": c["disciplina"]})

DADOS.mkdir(parents=True, exist_ok=True)
(DADOS / "banco_questoes_enem.json").write_text(json.dumps(banco, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"banco_questoes_enem.json: {len(banco)} questões")
print("  por matéria:", dict(Counter(q["materia"] for q in banco)))
print("  só texto (ideais para treino):", dict(Counter(q["materia"] for q in banco if not q["tem_imagem"])))
print("  descartadas:", dict(descartes))

# ---------- propostas de redação ----------
LIXO = re.compile(r"^(\*\d+AZ\d+\*|(ENE[MN]20\d\d)+E?|.*\| \dº DIA \|.*|.*• \dº DIA •.*|\d{1,2}|RASCUNHO|DA REDAÇÃO)$")
for ano in (2024, 2025):
    caderno = DOCS / f"enem{ano}_d1_caderno_azul.pdf"
    with fitz.open(caderno) as pdf:
        paginas = [i for i, p in enumerate(pdf, 1)
                   if "PROPOSTA DE REDAÇÃO" in p.get_text() or "INSTRUÇÕES PARA A REDAÇÃO" in p.get_text()]
        paginas = [p for p in paginas if p > 1]                          # a capa só cita a proposta
        blocos = [f"# Proposta de Redação — ENEM {ano} (INEP)",
                  f"Tema, instruções e textos motivadores do Caderno Azul do 1º dia do ENEM {ano}."]
        for p in paginas:
            linhas = [l.strip() for l in pdf[p - 1].get_text().splitlines()]
            texto = "\n".join(l for l in linhas if l and not LIXO.match(l))
            blocos.append(f"<!-- pagina: {p} -->\n{texto}")
    destino = DOCS / f"proposta_redacao_enem{ano}.md"
    destino.write_text("\n\n".join(blocos) + "\n", encoding="utf-8")
    tema = re.search(r"sobre o tema\s*“([^”]+)”", "\n".join(blocos).replace("\n", " "))
    print(f"{destino.name}: páginas {paginas} · tema: {tema.group(1) if tema else '?'}")
