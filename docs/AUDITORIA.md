# Auditoria do CKP03 — enunciado e rubrica × evidência

Auditoria feita em 28/10/2026 sobre a versão do repositório que acompanha este arquivo. Para cada exigência do
enunciado e item da rubrica: onde está no notebook e o que foi verificado (e como). Os números de "resultado" vêm do
*Run All* completo registrado no `.ipynb` (execução local com o mesmo código do Colab, `gemma4:cloud` real).

## 1. Exigências do enunciado

| # | Exigência | Onde | Verificação | Status |
|---|---|---|---|---|
| 1 | Agente com ≥ 3 tools | 7.10 | `assert len(kit) >= 3` para cada matéria; os kits têm 6 (Matemática: 7) | ✅ |
| 2 | 1 tool = RAG do CKP02 via `create_retriever_tool()`, description clara | 6 | `create_retriever_tool(...)` em `criar_tool_rag`; 7.10 confere que o 1º item do kit é esse objeto; description em 4 partes com exemplos e "NÃO use" | ✅ |
| 3 | 2+ tools adicionais com `@tool`, do domínio, descriptions bem escritas | 7.2–7.9 | 13 tools `@tool` (praticar, planejar, web, redação ×2, cálculo, estatística, guia, formulário, genética, DNA, fuso, escala); 7.10 confere "Use…" e "NÃO use…" em todas | ✅ |
| 4 | Chat EXCLUSIVAMENTE `gemma4:cloud` via Ollama Cloud | 2, 2.1 | `MODELO_LLM = "gemma4:cloud"` é o único modelo de chat (agentes, avaliadores da redação, expansão de consulta, resumos, LLM-juiz). O cross-encoder do reranking e o `nomic-embed-text` não são modelos de chat | ✅ |
| 5 | `OLLAMA_API_KEY` como Secret, nunca no código | 2.1 | `obter_segredo()` → `userdata.get`. Busca no repositório por padrões de chave: nenhuma ocorrência | ✅ |
| 6 | LangChain `AgentExecutor` (ReAct), como nas Aulas 09–11 | 8 | `create_react_agent` + `AgentExecutor` (de `langchain_classic`, mesma API do 1.x) | ✅ |
| 7 | Gradio com histórico e botão de limpar sessão | 11 | `gr.Blocks` + `gr.Chatbot` (histórico) + "🧹 Limpar sessão" (`limpar_sessao`: histórico, memória e estado das tools). Testado pela URL pública com `gradio_client` e navegador headless | ✅ |
| 8 | `demo.launch(share=True)` ativo na entrega + print/vídeo no README | 11, README | `COMPARTILHAR = True` → `launch(share=True, debug=False)`; prints da URL pública no README. **Pendente no dia:** vídeo da URL do dia e a URL no README (ver `ENTREGA.md`) | ⏳ no dia |
| 9 | 3 interações: 1 com RAG, 1 com outra tool, 1 sem tool | 10.1–10.3 | executadas com `verbose=True`; checagem automática da tool usada | ✅ |
| 10 | README com nomes e RMs de todos + print/vídeo da URL | README | tabela de integrantes; prints em `docs/assets/` | ✅ (vídeo no dia) |
| 11 | Entrega: Colab com leitura + `.ipynb` executado (Run All sem erros) + URL | — | *Run All* local sem erros salvo no `.ipynb`. **No dia:** Run All no Colab, salvar o `.ipynb` com as saídas, link com leitura | ⏳ no dia |

## 2. Diferenciais (+0,5 cada, até +1,0)

| Diferencial | Onde | Evidência |
|---|---|---|
| Guardrail de input (rejeitar fora do domínio com mensagem educada) | 9, 8 | camada 1 em código (injection e tamanho, sem LLM) + camada 2 no prompt (fora da matéria/ENEM → recusa educada indicando o tutor certo). 9.1: ataques bloqueados, mensagens legítimas liberadas, injeção disfarçada e pergunta fora da matéria recusadas pelo agente |
| Compressão de contexto (Observations: resumo + janela deslizante, Aula 10) | 8, 7.4 | memória = resumo pelo LLM + últimos 4 turnos; Observation da web resumida acima de 500 caracteres |
| Mais de 3 tools | 7.10 | 6 por agente, 7 na Matemática |

## 3. Rubrica

| Critério | Peso | O que o professor confere | Evidência |
|---|---|---|---|
| Agente funcional | 4,0 | 6 perguntas (2 RAG, 2 outra tool, 2 sem tool), os 3 exemplos e os logs | 10.5 simula as 6 perguntas e mostra a tool escolhida × esperada; 10.1–10.4 com logs `verbose` |
| RAG como tool | 2,5 | description clara, fontes citadas | description em 4 partes; Observation com `[Fonte: título, página — link]`; prompt exige citação; 10.1 confere a citação |
| Gradio + URL | 2,0 | histórico, usável por leigo | passos visíveis em linguagem simples, exemplos clicáveis, avisos, limpar sessão, sessão por aba |
| Descriptions + documentação | 1,5 | toda description com "quando usar" | 7.10 valida "Use…" e "NÃO use…" em todas; comentários `#` explicando o wording; markdown em todas as seções; `docs/` |

Checklist do professor: **o agente usa o RAG em ≥ 2 das 6 perguntas** (10.5 conta) · **toda description tem ao menos 1
frase de quando usar** (7.10 valida) · **testar a URL 30 min antes** (`ENTREGA.md`, passo 3).

## 4. Pedidos da Aula 11

| Pedido | Onde |
|---|---|
| Cada tool testada isolada com `invoke()` antes do agente | 6.1 (RAG) e 7.11 (70 testes de 13 tools, com caso de erro) |
| `verbose=True` nos logs | 8 (`AgentExecutor(verbose=True)`); logs nas saídas da Seção 10 |
| Exemplos com nota de qualidade 0,0–1,0 e pelo menos 1 multi-step | 10 (LLM-juiz + avaliação do grupo); 10.4 (RAG + calcular; sortear + corrigir) |
| Descriptions comentadas com `#` explicando o wording | 6, 7.x (cada parte da description tem um comentário) |
| Guardrail testado com tentativa de injection e output documentado | 9.1 |

## 5. Verificações técnicas feitas nesta auditoria

- **Execução:** *Run All* do zero (ChromaDB apagado, kernel novo) sem erro de célula.
- **Formato do notebook:** JSON com indent 1, UTF-8, CRLF (como o original); validado com `nbformat.validate`.
- **Segurança:** calculadora sem `eval` (árvore `ast` com whitelist), testada com `__import__('os')`, `().__class__`
  e `9^9^9`; nenhum segredo no repositório; Observations e mensagens tratadas como dados no prompt.
- **Dados conferidos:** os 38 verbetes da Matemática e os 17 exemplos do formulário de Física são executados e
  conferidos com `assert` no Run All; a tabela de 64 códons é conferida (20 aminoácidos, 3 de parada, AUG = Met);
  constantes físicas com valor de referência SI 2019/CODATA 2018 na descrição; fusos oficiais do Brasil (Decreto
  nº 9.772/2019; Acre UTC−5).
- **RAG:** isolamento por matéria testado (nenhum trecho de outra matéria); avaliação de recuperação em 14 perguntas
  (14/14 com a configuração final).

## 6. Limitações conhecidas (honestas)

- **Nota da redação é estimativa:** o INEP publica a Cartilha com a grade, mas não o manual dos corretores; a 7.5.1
  mede o quanto o corretor segue os critérios (o resultado fica na tabela da calibração).
- **Respostas do LLM variam** entre execuções (mesmo com `temperature=0`); por isso as checagens da Seção 10 são
  automáticas e a avaliação do grupo descreve a execução registrada.
- **Wikipédia:** a Wikimedia limita a taxa de acesso; a tool tenta de novo e, se falhar, devolve uma Observation com
  dica (o agente responde avisando que não conferiu a fonte).
- **URL do Gradio é temporária:** cai quando a sessão do Colab termina; por isso o checklist pede o teste 30 min antes
  e o Colab aberto durante a correção.
- **Questões com figura:** o banco prioriza questões sem figura no sorteio; quando há figura, a tool avisa e indica a
  página do caderno oficial.
