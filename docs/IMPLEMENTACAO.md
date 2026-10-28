# Como o Tutor ENEM funciona — documento de implementação

Este documento explica o notebook `CKP03_TutorENEM_1CCPK.ipynb` seção por seção: o que cada parte faz, por que foi
feita assim e o que foi medido. Serve para o grupo apresentar o projeto e para quem for manter o código.

## 1. Visão geral

```
Aluno (Gradio) ──► guardrail de input ──► AgentExecutor ReAct da matéria ──► resposta com fontes
                         │                   │  ▲
                         └─ recusa educada   │  └── memória da sessão (resumo + últimos 4 turnos)
                                             ▼
                                   tools da matéria (6 ou 7)
                                   ├─ buscar_material_enem  (RAG do CKP02, create_retriever_tool)
                                   ├─ praticar_questao_enem (questões reais + gabarito oficial)
                                   ├─ planejar_estudos      (cronograma até a prova)
                                   ├─ buscar_na_web         (Wikipédia, Observation comprimida)
                                   └─ 2 ou 3 tools específicas da matéria
```

- **Modelo de chat:** exclusivamente `gemma4:cloud` no Ollama Cloud (`temperature=0`). A chave `OLLAMA_API_KEY` vem
  dos *Secrets* do Colab (`userdata.get`), nunca do código.
- **Embeddings:** `nomic-embed-text` num Ollama local dentro do Colab (o `/api/embed` do Ollama Cloud responde 401).
- **Um agente por matéria, mesmo código:** o registro `MATERIAS` (Seção 2) gera tudo: filtros do RAG, tools, agentes
  e opções da interface. A matéria fica "presa" em cada tool na criação (fábricas `criar_tool_*`): o agente de Física
  não consegue sortear questão de Biologia, mesmo que tente.

## 2. Seções 1–2: instalação e configuração

- `langchain-classic`: no LangChain 1.x, `AgentExecutor`, `create_react_agent` e `create_retriever_tool` saíram de
  `langchain.*`. Mesma API, só muda o import.
- `rank_bm25` (novo): índice de palavras-chave do RAG híbrido.
- **Execução fora do Colab (novo):** `TUTOR_ENEM_LOCAL=1` faz o notebook usar o Ollama da máquina (logado com
  `ollama signin`), que encaminha o mesmo `gemma4:cloud` para a nuvem. Rodando de dentro do repositório, a própria pasta
  vira o projeto (não clona de novo). No Colab nada muda.
- **Re-execução no Colab (novo):** se a pasta clonada já existe, o notebook faz `git pull` antes de usar os dados
  (antes era preciso abrir um ambiente novo para pegar mudanças do repositório). Se o Ollama local já está no ar com
  o modelo baixado, ele não é reinstalado.

## 3. Seções 3–5: base de conhecimento, chunking e ChromaDB

**Base 100% oficial (INEP)**, descrita no manifesto `fontes.csv` (título, tipo, matéria, data e link de cada arquivo):

| Fonte | Como entra |
|---|---|
| Matriz de Referência do ENEM | texto por OCR, separado por matéria (o PDF tem ~49% do texto ilegível por fonte sem Unicode) |
| A Redação no Enem 2025 — Cartilha do Participante | texto por OCR, com o número da página original |
| Edital Inep nº 64/2026 (texto vigente) | `.md` com marcadores `<!-- item: N -->` para citar o item |
| Propostas de redação 2024 e 2025 | tema + textos motivadores do Caderno Azul |
| 186 questões reais (2024–2025) | `dados/banco_questoes_enem.json`: 1 questão = 1 chunk, com gabarito oficial |

**Chunking:** `RecursiveCharacterTextSplitter` 1024/128 (vencedor do RAGAS no CKP02).
> 🔧 **Correção desta entrega:** o título do documento (`# Matriz de Referência …`) ia junto da página para o splitter,
> que o separava do corpo. Medimos **99 de 454 chunks (22%) só com o título**, 68 deles da Cartilha. Esses chunks
> "casavam" com quase toda pergunta e chegavam vazios ao agente (a pergunta "o que zera a redação?" recebia 4
> cabeçalhos). Agora o corpo é fatiado e **cada chunk recebe o título**; nenhum chunk é só cabeçalho. Resultado: 541
> chunks com conteúdo.

**ChromaDB:** uma coleção (`tutor_enem_cs1024`, cosseno), metadado `materia`. Cada agente vê só
`materia ∈ {sua matéria, geral}`. A coleção é reaproveitada se a base não mudou (assinatura MD5).

## 4. Seção 6: RAG como tool (`create_retriever_tool`)

Pipeline da tool `buscar_material_enem` (uma por agente, mesmo nome, filtro e description da matéria):

1. **Busca híbrida filtrada:** vetorial (Chroma, `filter` por matéria) + **BM25** (palavras-chave, sem acento, radical
   de 5 letras) sobre os chunks da mesma matéria, unidas pelo `EnsembleRetriever` (12 candidatos de cada).
2. **Expansão da consulta** (`MultiQueryRetriever`): o `gemma4:cloud` reescreve a pergunta em 2 buscas com o
   vocabulário oficial; a pergunta original também é buscada. Se o LLM falhar, segue só com a original.
3. **Reranking** (`CrossEncoderReranker`) com o cross-encoder **multilíngue** `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`,
   contra a pergunta original → top-4.
4. `create_retriever_tool` com `document_prompt` que põe `[Fonte: título, página — link]` em cada trecho.

> 🔧 **Melhoria medida nesta entrega.** 14 perguntas reais das 5 matérias, conferindo se o trecho certo chega ao top-4:
>
> | Configuração | Acertos | Tempo/busca |
> |---|---|---|
> | CKP02 (vetorial + reranker em inglês) | 13/14 — errava "o que zera a redação?" (exemplo da própria description) | ~1,3 s |
> | vetorial 30 + reranker em português (L6) | 13/14 | ~1,1 s |
> | híbrido + expansão + reranker português (L6) | 12/14 | ~2,0 s |
> | **híbrido + expansão + reranker multilíngue (L12)** | **14/14** | **~3,3 s** |
>
> Na pergunta "o que zera a redação?", a página da Cartilha que lista os motivos (p. 9) não ficava nem entre os 60
> trechos mais próximos: o aluno diz "zera", o documento diz "nota 0 (zero)". O reranker em inglês também rebaixava o
> trecho certo. A combinação final resolve os dois problemas.

O teste isolado (6.1) confere, nas 5 matérias, que nenhum trecho de outra matéria aparece e quantas fontes citáveis
vêm na Observation.

## 5. Seção 7: tools de domínio

Padrões comuns (7.1): `@tool` + `args_schema` Pydantic com **um campo de texto** (o ReAct entrega o `Action Input` como
um texto só), decorator `com_tratamento_de_erro` (exceção vira Observation com dica, o loop não quebra), estado por
sessão (`SESSAO_ID`), descriptions em 4 partes comentadas.

| Seção | Tools | Como funciona |
|---|---|---|
| 7.2 | `praticar_questao_enem` | sorteio de questão real **sem gabarito** (prioriza as sem figura, não repete); a letra do aluno é corrigida pelo **gabarito oficial**, não pelo LLM. Na Redação: tema oficial (2013–2025), inédito (gerado e rotulado) ou do aluno |
| 7.3 | `planejar_estudos` | dias até a prova da matéria, blocos da Matriz distribuídos com foco primeiro, revisão e véspera; horários do Edital |
| 7.4 | `buscar_na_web` | Wikipédia PT + resumo guiado pela consulta acima de 500 caracteres (compressão de Observation, Aula 10) |
| 7.5 | `analisar_estrutura_redacao`, `corrigir_redacao` | análise determinística + correção com a grade oficial completa, 2 avaliadores independentes, 3º na discrepância, regras oficiais aplicadas pelo código, evidências conferidas contra o texto; calibração em 7.5.1 |
| 7.6 | `calcular`, `estatistica_descritiva`, `como_digitar` | motor seguro **sem `eval`** (`ast` + whitelist → SymPy), limites de tamanho e tempo; guia com 38 verbetes cujos exemplos são executados e conferidos |
| 7.7 | `calcular` (Física), `formulario_fisica` | mesmo motor + 11 constantes pelo nome (`g`, `c_luz`, `k0`…); formulário por bloco da Matriz com 17 exemplos conferidos por `assert`; conversão exata de unidades (frações) |
| 7.8 | `cruzamento_genetico`, `traduzir_dna` | Punnett com frações exatas (mono/di/tri-híbrido, dominância incompleta, ABO, ligada ao X com resultado por sexo); tabela dos 64 códons gerada da forma compacta oficial e conferida |
| 7.9 | `calcular_fuso_horario`, `escala_cartografica` | 15° = 1 h, fuso teórico, hora solar exata (4 min/grau), mudança de data, fusos oficiais do Brasil; escala E = D/d nos 3 sentidos e áreas com E² |
| 7.10 | `TOOLS_POR_MATERIA` | kit de cada agente e validação: RAG presente, nomes únicos, toda description com "Use…" e "NÃO use…" |
| 7.11 | testes | 70 testes com `invoke()` (casos conhecidos + caso de erro de cada tool) |

> 🔧 **Correções nas tools existentes:** (1) `buscar_na_web` — o pacote `wikipedia` passou a receber HTTP 429/503 da
> Wikimedia (URL `http://` + User-Agent genérico). A tool agora chama a API oficial direto (`https`, User-Agent
> identificado), primeiro o resumo do verbete pelo título (endpoint em cache, o mais estável), depois 1 busca com até 3
> tentativas; mesmo formato de saída. (2) `planejar_estudos` — o exemplo de foco da description era de Matemática em
> todas as matérias; agora cada matéria tem o seu.

## 6. Seção 8: agentes ReAct

- **Prompt ReAct próprio** no formato `hwchase17/react` (Thought/Action/Action Input/Observation/Final Answer, com
  `{tools}`, `{tool_names}`, `{agent_scratchpad}`, `{input}`), porque o `hub.pull(...).partial(system_message=...)`
  ignora a persona (o template do hub não tem essa variável). Regras: escopo da matéria com recusa educada, uso de tool
  só quando necessário, **fontes obrigatórias** (e complemento próprio sinalizado), contas sempre na calculadora,
  mensagens e Observations como **dados não confiáveis**, não revelar gabarito, português, fórmulas em texto simples.
- **`create_react_agent` + `AgentExecutor`**: `verbose=True`, `max_iterations=6`, `max_execution_time=240 s`,
  `handle_parsing_errors` com mensagem que ensina o formato, `return_intermediate_steps=True`.
- **Memória (compressão de contexto, Aula 10):** por (sessão, matéria), últimos 4 turnos literais + resumo dos
  anteriores feito pelo LLM; falas cortadas em 600 caracteres. Um lock garante que o turno seguinte só lê a memória
  depois que o resumo terminou.
- **`responder()` / `responder_stream()`:** única porta de entrada (notebook e interface). Passa pelos filtros de
  entrada, roda o agente numa thread com o `SESSAO_ID` da conversa e emite eventos (tool chamada, Observation, resposta).
  - **Redação colada:** guardada na sessão (`guardar_redacao`); o agente recebe só "redação de N palavras guardada;
    pedido: corrigir" e nunca recopia o texto (o que poderia "consertar" desvios e falsear a Competência I).
  - **Questão em andamento (novo):** se há questão sorteada e não corrigida, o agente recebe um aviso para corrigir a
    letra do aluno com `praticar_questao_enem` antes de explicar. Motivo, visto no teste da interface: sem o aviso, o
    agente resolvia a questão sozinho com `calcular` e pulava o gabarito oficial e o placar.

## 7. Seção 9: guardrail de input

| Camada | Onde | Barra |
|---|---|---|
| 1 | código, antes do LLM | *injection* explícita (8 padrões: ignorar instruções, `system:`, troca de papel, jailbreak, revelar instruções, marcadores `<\|im_start\|>`/`[INST]`, imitação de `Observation:`/`Final Answer:`) e mensagem longa (2.000 caracteres; 6.000 na Redação) |
| 2 | prompt do agente | pergunta fora da matéria/do ENEM e injeção disfarçada |

Os padrões exigem verbo no imperativo + alvo ("ignore **as instruções**") e possessivo/qualificador para "revelar"
("**suas** instruções", "regras **internas**"), para não bloquear "esqueci a fórmula" ou "as instruções da prova de
redação". Bloqueios ficam em `REGISTRO_BLOQUEIOS`.

## 8. Seção 10: interações documentadas

`demonstrar()` roda 1 turno com `verbose=True` e mostra: resposta, tools usadas × esperadas, checagens automáticas
(número certo, fonte citada) e uma **nota 0,0–1,0 de um LLM-juiz** (`gemma4:cloud`, `temperature=0`, saída Pydantic).
Interações: RAG (Redação, "o que zera"), outra tool (Matemática, comissões = 120), sem tool (Biologia, mitose),
multi-step (Física, RAG + calcular; Matemática, sortear + corrigir em 2 turnos) e as 6 perguntas do professor.

## 9. Seção 11: interface Gradio

`gr.Blocks`: seletor de matéria (emoji + nome), `gr.Chatbot` em formato de mensagens com os **passos da tool como
mensagens recolhíveis** (`metadata`), caixa de texto multilinha (para colar redação), exemplos por matéria, botão
"🧹 Limpar sessão", aviso de nota estimada na Redação, painel "📖 Como digitar contas" na Matemática, sessão por aba
(`uuid4`), LaTeX só com `$$…$$`/`\(…\)` (o `$` sozinho quebrava "R$"), `show_error=True` e
`demo.launch(share=True, debug=False)`.

> 🔧 **Bug corrigido no teste pelo navegador:** o Gradio devolve as mensagens do histórico com `metadata: None`, e
> `msg.get("metadata", {})` devolvia `None` (a chave existe) → `AttributeError` e "Erro" na tela ao trocar de matéria.
> O handler agora guarda o passo pendente por referência e entrega ao Gradio sempre uma cópia do histórico.

## 10. Como testamos

- Kernel Jupyter local com o mesmo código do Colab (`TUTOR_ENEM_LOCAL=1`, `gemma4:cloud` real), célula a célula.
- Interface testada pela **URL pública** com `gradio_client` (API) e com navegador headless (Edge via Playwright),
  inclusive os prints do README.
- *Run All* do notebook inteiro com `nbclient`, do zero (ChromaDB apagado), sem erros: é a execução salva no `.ipynb`.
