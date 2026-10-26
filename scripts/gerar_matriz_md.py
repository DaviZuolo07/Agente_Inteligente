"""Gera a Matriz de Referência do ENEM em Markdown limpo, separada por matéria.

Por quê: o PDF oficial (download.inep.gov.br/enem/outros_documentos/enem_matriz_referencia.pdf) usa uma fonte sem
mapeamento Unicode — ~49% do texto extraído pelo PyMuPDF sai como símbolos ilegíveis, o que inutiliza a busca. Este
script lê o texto obtido por OCR (tesseract, idioma por, 300 dpi) das páginas do PDF oficial, corrige os erros
sistemáticos do OCR e grava um .md por matéria, com marcadores <!-- pagina: N --> que preservam a página ORIGINAL do PDF
para a citação da fonte.

Uso: python gerar_matriz_md.py <pasta_com_mat-NN.txt> <pasta_docs_de_saida>
"""
import re
import sys
from pathlib import Path

ORIGEM, DESTINO = Path(sys.argv[1]), Path(sys.argv[2])

# arquivo de saída → (título, páginas do PDF oficial, cortar a página no marcador)
PARTES = {
    "matriz_eixos_cognitivos.md":    ("Eixos cognitivos comuns a todas as áreas", [2, 17]),
    "matriz_matematica.md":          ("Matemática e suas Tecnologias", [7, 8, 9, 21, 22]),
    "matriz_ciencias_natureza.md":   ("Ciências da Natureza — competências e habilidades", [10, 11, 12, 13]),
    "matriz_fisica.md":              ("Ciências da Natureza — objetos de conhecimento de Física", [23, 24, 25, 26]),
    "matriz_biologia.md":            ("Ciências da Natureza — objetos de conhecimento de Biologia", [31, 32, 33]),
    "matriz_ciencias_humanas.md":    ("Ciências Humanas e suas Tecnologias", [14, 15, 16, 34, 35, 36]),
}
CORTES = {26: "QUÍMICA"}          # a p. 26 termina Física e começa Química: fica só a parte de Física
RUIDO = re.compile(r"(defeso eleitoral|MATIAE|^mer$|^\W{0,3}\w{0,3}\W{0,3}$|^Dad o|^” o ”|^\d{1,2}$)")


def limpar_pagina(texto: str, numero: int) -> str:
    if numero in CORTES and CORTES[numero] in texto:
        texto = texto.split(CORTES[numero])[0].rstrip(" |\n")
    linhas = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or RUIDO.search(linha):
            continue
        linha = re.sub(r"^(DD»?|\|)\s*", "### ", linha)                 # marcador de seção dos objetos de conhecimento
        linha = re.sub(r"^[eéºoO]\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", "- ", linha)  # bullet lido como 'e', 'é', 'º' ou 'o'
        linha = re.sub(r"Competência de área\s*&?(\d)", r"Competência de área \1", linha)
        linha = re.sub(r"\bOU\b", "ou", linha)
        linhas.append(linha)
    return "\n".join(linhas)


def renumerar_habilidades(texto: str) -> str:
    """O OCR troca dígitos nos códigos (H1O, HT1, HT16). As habilidades são sequenciais dentro de cada área,
    então o código é refeito pela ordem de aparição."""
    contador = 0

    def proxima(m):
        nonlocal contador
        contador += 1
        return f"H{contador} —"
    return re.sub(r"^H[á\dTIlO]{1,3}\s*[—–-]+", proxima, texto, flags=re.MULTILINE)   # 'Há' = H4 lido errado


DESTINO.mkdir(parents=True, exist_ok=True)
for arquivo, (titulo, paginas) in PARTES.items():
    blocos = [f"# Matriz de Referência do ENEM (INEP) — {titulo}",
              "Texto do PDF oficial do INEP, obtido por OCR (o PDF original tem fonte sem mapeamento Unicode)."]
    for p in paginas:
        bruto = (ORIGEM / f"mat-{p:02d}.txt").read_text(encoding="utf-8")
        blocos.append(f"<!-- pagina: {p} -->\n{limpar_pagina(bruto, p)}")
    texto = "\n\n".join(blocos)
    if "habilidades" in titulo or arquivo in ("matriz_matematica.md", "matriz_ciencias_humanas.md"):
        texto = renumerar_habilidades(texto)
    (DESTINO / arquivo).write_text(texto + "\n", encoding="utf-8")
    print(f"{arquivo}: {len(texto):,} caracteres · páginas {paginas}")
