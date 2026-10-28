# Entrega do CKP03 — checklist e mensagem

Prazo: **29/10/2026, 23:59**, pelo Teams (só o líder, Davi, envia).

## Checklist do dia

1. **Colab novo, do zero:** abrir o [notebook no Colab](https://colab.research.google.com/github/DaviZuolo07/Agente_Inteligente/blob/main/CKP03_TutorENEM_1CCPK.ipynb)
   (*Runtime → Disconnect and delete runtime* se já estava aberto), conferir o Secret `OLLAMA_API_KEY` com acesso
   liberado e rodar *Runtime → Run all*. Leva ~15–25 min (instala o Ollama local, indexa, calibra a redação, roda as
   interações da Seção 10).
2. Conferir que **nenhuma célula deu erro** e que a última imprimiu `🌐 URL pública do Tutor ENEM: https://….gradio.live`.
3. **Testar a URL 30 min antes** (checklist do professor), de preferência no celular: Física → 1º exemplo; Redação →
   "O que zera a redação no ENEM?"; Matemática → "Me passa uma questão de porcentagem" e responder a letra; 🧹 Limpar sessão.
4. **Print/vídeo:** gravar 30–60 s usando a URL pública (barra de endereço visível) e salvar em `docs/assets/`
   (ex.: `url_publica.mp4` ou `url_publica.png`). No `README.md`, trocar `https://________________.gradio.live`
   pela URL do dia e linkar o arquivo.
5. **Salvar o `.ipynb` executado:** no Colab, *File → Download → Download .ipynb* e substituir o
   `CKP03_TutorENEM_1CCPK.ipynb` do repositório (ou *File → Save a copy in GitHub*). Assim a versão entregue tem as
   saídas da execução no Colab, com a URL do dia.
6. Conferir que **nenhuma chave** aparece no notebook nem no repositório (a chave só existe nos Secrets).
7. **Colab com permissão de leitura:** *Share → General access → Anyone with the link → Viewer*. (O link
   `colab.research.google.com/github/...` abre direto do GitHub público e já é só leitura.)
8. `git add` + `git commit` + `git push` (o GitHub pede **token**, não senha).
9. **Manter o Colab aberto e ativo** durante a janela de correção: a URL do Gradio cai quando a sessão termina. Se
   cair, rodar de novo e atualizar a URL no README/Teams.

## Mensagem para o Teams

> **CKP03 — Tutor ENEM 2026 (Agente Inteligente) · Turma 1CCPK**
>
> Grupo: Davi Queiroz Zuolo (RM 571669) · Daniel Vilela Mana (RM 571632) · Gustavo Zagato Bottechia (RM 569420) · Kayo Henderson (RM 570706)
>
> - Colab (leitura): https://colab.research.google.com/github/DaviZuolo07/Agente_Inteligente/blob/main/CKP03_TutorENEM_1CCPK.ipynb
> - Repositório (README com print/vídeo da URL ativa, notebook executado e documentação): https://github.com/DaviZuolo07/Agente_Inteligente
> - URL pública do Gradio: https://________________.gradio.live
>
> Agente ReAct (create_react_agent + AgentExecutor) com gemma4:cloud via Ollama Cloud (chave em Secret), 1 agente por
> matéria (Redação, Matemática, História & Geografia, Biologia, Física), 6–7 tools cada — incluindo o RAG do CKP02 via
> create_retriever_tool —, guardrail de input, memória com compressão (resumo + janela) e interface Gradio com histórico
> e botão de limpar sessão. As 3 interações pedidas (RAG, outra tool, sem tool) estão na Seção 10 do notebook, com os
> logs verbose.
