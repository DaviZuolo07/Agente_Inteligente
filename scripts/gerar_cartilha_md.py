"""Gera a Cartilha da Redação 2025 em Markdown limpo, a partir de OCR, mantendo a página original.

Por quê: parte dos glifos da fonte do PDF oficial não tem mapeamento Unicode. O PyMuPDF devolve ~500 linhas ilegíveis
espalhadas por 57 das 78 páginas (ex.: '$V DXODV VREUH HVFUDYLGmR' no lugar de 'As aulas sobre escravidão'). O OCR
(tesseract, português, 300 dpi) lê o texto como ele aparece na página. O OCR também lê as imagens decorativas e gera
lixo nelas; esse lixo é filtrado com um vocabulário montado a partir das linhas LIMPAS do próprio PDF.

Uso: python gerar_cartilha_md.py <pdf_oficial> <pasta_com_c-NN.txt> <arquivo_saida.md>
"""
import re
import sys
from pathlib import Path

import fitz

PDF, PASTA_OCR, SAIDA = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
PALAVRAS_FUNCAO = set("de que e a o da do das dos para com não em os as uma um no na nos nas se é por ao à ou como "
                      "mais sua seu suas seus ser sobre pela pelo".split())
PALAVRA = re.compile(r"[A-Za-zÀ-ÿ]+")


def vocabulario_do_pdf(pdf: Path) -> set[str]:
    """Palavras das linhas do PDF que vieram legíveis (têm palavra-função e nenhum caractere de controle)."""
    vocab = set()
    with fitz.open(pdf) as doc:
        for pagina in doc:
            for linha in pagina.get_text().splitlines():
                palavras = [p.lower() for p in PALAVRA.findall(linha)]
                if re.search(r"[\x00-\x08\x0b-\x1f]", linha) or not PALAVRAS_FUNCAO & set(palavras):
                    continue
                vocab.update(palavras)
    return vocab | PALAVRAS_FUNCAO


def linha_valida(linha: str, vocab: set[str]) -> bool:
    palavras = [p.lower() for p in PALAVRA.findall(linha)]
    if not palavras:
        return bool(re.fullmatch(r"\s*[\d.,%()–—-]+\s*", linha)) and len(linha.strip()) > 2
    if re.fullmatch(r"[a-zà-ÿ]{3,}[;.,:)]?", linha.strip()):      # fim de frase quebrado em linha própria ("sustentam;")
        return True
    conhecidas = sum(1 for p in palavras if p in vocab or len(p) == 1 and p in "aeo")
    return conhecidas / len(palavras) >= 0.7 and (len(palavras) >= 2 or palavras[0] in vocab and len(palavras[0]) > 3)


def vocabulario_do_ocr(pasta: Path) -> set[str]:
    """Completa o vocabulário com frases do OCR que são claramente texto corrido (≥ 6 palavras, ≥ 2 palavras-função)."""
    vocab = set()
    for arq in pasta.glob("c-*.txt"):
        for linha in arq.read_text(encoding="utf-8").splitlines():
            palavras = [p.lower() for p in PALAVRA.findall(linha)]
            if len(palavras) >= 6 and len(PALAVRAS_FUNCAO & set(palavras)) >= 2:
                vocab.update(p for p in palavras if len(p) > 1)
    return vocab


vocab = vocabulario_do_pdf(PDF) | vocabulario_do_ocr(PASTA_OCR)
total = mantidas = 0
blocos = ["# A Redação no Enem 2025 — Cartilha do(a) Participante (INEP)",
          "Texto do PDF oficial do INEP obtido por OCR (parte da fonte do PDF não tem mapeamento Unicode)."]
for arq in sorted(PASTA_OCR.glob("c-*.txt"), key=lambda p: int(p.stem.split("-")[1])):
    numero = int(arq.stem.split("-")[1])
    linhas = [l.strip() for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()]
    total += len(linhas)
    boas = [l for l in linhas if linha_valida(l, vocab)]
    mantidas += len(boas)
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", "\n".join(boas))
    if len(texto) >= 30:
        blocos.append(f"<!-- pagina: {numero} -->\n{texto}")
SAIDA.write_text("\n\n".join(blocos) + "\n", encoding="utf-8")
print(f"{SAIDA.name}: {mantidas}/{total} linhas mantidas · vocabulário de {len(vocab):,} palavras · "
      f"{SAIDA.stat().st_size:,} bytes")
