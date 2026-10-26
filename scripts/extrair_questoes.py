"""Extrai as questões objetivas dos cadernos oficiais do ENEM (INEP) e junta com o gabarito oficial.

Entrada : docs/enem{ano}_d{dia}_caderno_azul.pdf + docs/enem{ano}_d{dia}_gabarito.pdf (2024 e 2025)
Saída   : dados/questoes_extraidas.json — todas as questões de Ciências Humanas (46–90), Ciências da Natureza (91–135)
          e Matemática (136–180), com enunciado, alternativas A–E, página, gabarito e sinal de figura.
          (Linguagens 1–45 fica de fora: não há tutor dessa área.)

Como funciona: o caderno é diagramado em 2 colunas. Os blocos de texto do PyMuPDF são ordenados por
(página, coluna, altura), cabeçalho/rodapé são descartados, e o fluxo é cortado em "QUESTÃO N"/"Questão N".
As alternativas são as últimas linhas iniciadas por "A<tab>" … "E<tab>".

Uso: python extrair_questoes.py <pasta_docs> <arquivo_saida.json>
"""
import json
import re
import sys
from pathlib import Path

import fitz

DOCS, SAIDA = Path(sys.argv[1]), Path(sys.argv[2])
MEIO_DA_PAGINA = 285                      # x que separa as duas colunas do caderno
AREAS = [(46, 90, "ciencias_humanas"), (91, 135, "ciencias_natureza"), (136, 180, "matematica")]
CABECALHO = re.compile(r"^(\*\d+AZ\d+\*|(ENEM20\d\d)+|.*• \d?º? ?DIA •.*|.*CADERNO \d+ • AZUL.*|"
                       r"(CIÊNCIAS|MATEMÁTICA|LINGUAGENS).*\n?Questões de \d+ a \d+.*)", re.S)
INICIO_QUESTAO = re.compile(r"^\s*QUEST[ÃA]O\s+0?(\d{1,3})\b", re.I)
PALAVRAS_FIGURA = re.compile(r"\b(figura|gráfico|imagem|mapa|charge|tabela|esquema|ilustra\w*|infográfico|"
                             r"quadro|tirinha|fotografia|foto|cartum|representad[ao] (a seguir|abaixo|na))\b", re.I)


def area_da_questao(numero: int) -> str | None:
    return next((nome for ini, fim, nome in AREAS if ini <= numero <= fim), None)


SOBRESCRITO = str.maketrans("0123456789+-−()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻⁽⁾ⁿ")


def texto_do_bloco(bloco: dict) -> str:
    """Texto do bloco preservando EXPOENTES: o texto simples do PDF transforma 10⁴ em '104' e m² em 'm2',
    o que muda a resposta de questões de Física e Matemática. Spans com a flag de sobrescrito viram ⁰¹²³…"""
    linhas = []
    for linha in bloco.get("lines", []):
        partes = []
        for span in linha["spans"]:
            t = span["text"]
            if span["flags"] & 1 and t.strip() and all(c in "0123456789+-−()n " for c in t):
                t = t.strip().translate(SOBRESCRITO)
            partes.append(t)
        linhas.append("".join(partes))
    return "\n".join(linhas)


def blocos_ordenados(pdf: fitz.Document):
    """(página, coluna, y, texto, bbox) dos blocos de texto, sem cabeçalho/rodapé, na ordem de leitura."""
    blocos = []
    for num_pag, pagina in enumerate(pdf, start=1):
        altura = pagina.rect.height
        for bloco in pagina.get_text("dict")["blocks"]:
            if bloco.get("type") != 0:
                continue
            x0, y0, x1, y1 = bloco["bbox"]
            t = texto_do_bloco(bloco).strip()
            # o título da área às vezes vem no MESMO bloco da 1ª questão ("...Questões de 46 a 90\nQUESTÃO 46")
            t = re.sub(r"^(CIÊNCIAS|MATEMÁTICA|LINGUAGENS)[^\n]*\n(?:[^\n]*\n)?Questões de \d+ a \d+[^\n]*\n?", "", t)
            if not t or y0 > altura - 40 or y1 < 60 or CABECALHO.match(t):
                continue
            coluna = 0 if x0 < MEIO_DA_PAGINA else 1
            blocos.append((num_pag, coluna, y0, t, (x0, y0, x1, y1)))
    return sorted(blocos, key=lambda b: (b[0], b[1], b[2]))


def regioes_de_figura(pdf: fitz.Document) -> dict[int, list[fitz.Rect]]:
    """Retângulos de imagens por página (logotipos minúsculos são ignorados)."""
    figuras = {}
    for num_pag, pagina in enumerate(pdf, start=1):
        rects = [fitz.Rect(info["bbox"]) for info in pagina.get_image_info()]
        figuras[num_pag] = [r for r in rects if r.width > 40 and r.height > 30]
    return figuras


def separar_alternativas(texto: str) -> tuple[str, dict[str, str]]:
    """Divide enunciado e alternativas. Procura a ÚLTIMA sequência A, B, C, D, E no início de linha."""
    linhas = texto.split("\n")
    posicoes = {}
    for i, linha in enumerate(linhas):
        m = re.match(r"^([A-E])[\t ]+(.*)", linha)
        if m:
            posicoes.setdefault(m.group(1), []).append(i)
    if not all(letra in posicoes for letra in "ABCDE"):
        return texto.strip(), {}
    # a sequência válida é a última em que A < B < C < D < E
    for ia in reversed(posicoes["A"]):
        seq, atual = [ia], ia
        for letra in "BCDE":
            proxima = next((p for p in posicoes[letra] if p > atual), None)
            if proxima is None:
                break
            seq.append(proxima)
            atual = proxima
        if len(seq) == 5:
            break
    else:
        return texto.strip(), {}
    enunciado = "\n".join(linhas[:seq[0]]).strip()
    alternativas = {}
    limites = seq + [len(linhas)]
    for k, letra in enumerate("ABCDE"):
        trecho = "\n".join(linhas[limites[k]:limites[k + 1]])
        alt = re.sub(r"\s+", " ", re.sub(r"^[A-E][\t ]+", "", trecho)).strip()
        # crédito de figura de OUTRA questão que caiu logo depois da alternativa E na ordem de leitura
        alternativas[letra] = re.sub(r"\s*(Disponível em:|Acesso em:|Fonte:).*$", "", alt).strip()
    return enunciado, alternativas


def ler_gabarito(caminho: Path) -> dict[int, str]:
    texto = "\n".join(p.get_text() for p in fitz.open(caminho))
    texto_layout = re.sub(r"[ \t]+", " ", texto)
    pares = re.findall(r"(?<!\d)(\d{2,3})\s+(Anulad[oa]|[A-E])\b", texto_layout)
    return {int(n): ("ANULADA" if g.lower().startswith("anulad") else g) for n, g in pares if 46 <= int(n) <= 180}


def limpar(texto: str) -> str:
    texto = texto.replace("\t", " ")
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)
    texto = re.sub(r"[ ]+\n", "\n", texto)
    texto = re.sub(r"(?<![.:;?!)”\"])\n(?=[a-zà-ú(])", " ", texto)     # junta linhas quebradas no meio da frase
    return re.sub(r"\n{2,}", "\n", texto).strip()


def extrair(ano: int, dia: int) -> list[dict]:
    caderno = DOCS / f"enem{ano}_d{dia}_caderno_azul.pdf"
    gabarito = ler_gabarito(DOCS / f"enem{ano}_d{dia}_gabarito.pdf")
    pdf = fitz.open(caderno)
    figuras = regioes_de_figura(pdf)
    questoes, atual = [], None
    for pagina, coluna, y, texto, bbox in blocos_ordenados(pdf):
        m = INICIO_QUESTAO.match(texto)
        if m:
            if atual:
                questoes.append(atual)
            numero = int(m.group(1))
            resto = texto[m.end():].strip()
            atual = {"numero": numero, "pagina": pagina, "partes": [resto] if resto else [],
                     "inicio": (pagina, coluna, y)}
            continue
        if atual:
            atual["partes"].append(texto)
    if atual:
        questoes.append(atual)

    # figura → questão dona: a última questão que começa antes da figura na ordem de leitura (página, coluna, y)
    inicios = sorted((q["inicio"], i) for i, q in enumerate(questoes))
    com_figura = set()
    for pagina, rects in figuras.items():
        for r in rects:
            pos = (pagina, 0 if (r.x0 + r.x1) / 2 < MEIO_DA_PAGINA else 1, r.y0)
            anteriores = [i for inicio, i in inicios if inicio <= pos]
            if anteriores:
                com_figura.add(anteriores[-1])

    saida, vistas = [], set()
    for indice, q in enumerate(questoes):
        area = area_da_questao(q["numero"])
        if not area or q["numero"] in vistas:          # Linguagens ou número repetido (inglês/espanhol)
            continue
        vistas.add(q["numero"])
        texto = "\n".join(q["partes"])
        enunciado_bruto, alternativas = separar_alternativas(texto)
        tem_imagem = indice in com_figura
        gab = gabarito.get(q["numero"], "")
        saida.append({
            "id": f"{ano}-D{dia}-{q['numero']:03d}", "ano": ano, "dia": dia, "numero": q["numero"], "area": area,
            "enunciado": limpar(enunciado_bruto), "alternativas": alternativas,
            "gabarito": "" if gab == "ANULADA" else gab, "anulada": gab == "ANULADA",
            "pagina": q["pagina"], "fonte_arquivo": caderno.name,
            "tem_imagem": tem_imagem or bool(PALAVRAS_FIGURA.search(enunciado_bruto)),
            "extracao_ok": len(alternativas) == 5 and bool(gab),
        })
    return saida


todas = []
for ano in (2024, 2025):
    for dia in (1, 2):
        lote = extrair(ano, dia)
        ok = sum(q["extracao_ok"] for q in lote)
        print(f"ENEM {ano} dia {dia}: {len(lote)} questões · {ok} completas · "
              f"{sum(q['tem_imagem'] for q in lote)} com figura · {sum(q['anulada'] for q in lote)} anuladas")
        todas.extend(lote)
SAIDA.parent.mkdir(parents=True, exist_ok=True)
SAIDA.write_text(json.dumps(todas, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Total: {len(todas)} questões → {SAIDA}")
