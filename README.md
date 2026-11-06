![Thread Notes — a conversa continua após reiniciar](brand/banner.svg)

# Thread Notes API

Publicações e comentários para organizar notas de aula ou discussões de um pequeno projeto. Crie textos, filtre publicações e acompanhe seus comentários sem perder os registros ao reiniciar.

**Dia 04/10 · 06/11/2026 · Python 3.10+ · SQLite · sem pacotes externos · 12 testes HTTP aprovados**

[Rotas](#rotas) · [Verificação](VERIFICATION.md) · [Anúncio](ANNOUNCEMENT.md) · [LinkedIn](LINKEDIN.md) · [Contribuir](CONTRIBUTING.md)

Implementação própria inspirada em recursos aninhados e filtros do JSONPlaceholder. Usa dados próprios, começa com banco vazio e não consulta o serviço de referência. Publicar código no GitHub não hospeda esta API: execução local, sem interface gráfica ou endpoint público.

## Comece aqui

Python 3.10 ou superior com módulo sqlite3. Verificado em Linux com Python **3.12.14**. Não precisa pip.

```bash
git clone https://github.com/perabru/api-lab-2026-11-06.git
cd api-lab-2026-11-06
python src/server.py
```

Em sistemas em que o executável se chama python3, substitua python nos comandos. Padrão: http://127.0.0.1:3000.

### Primeiro fluxo — banco vazio

```bash
curl http://127.0.0.1:3000/health
curl -i -X POST http://127.0.0.1:3000/posts \
  -H 'Content-Type: application/json' \
  -d '{"author":"Bruno","title":"Aula HTTP","body":"Uma nota para a turma"}'
```

Health: 200, `{"status":"ok"}`. Criação: **201**, Location: /posts/1, resposta verificada:

```json
{"id":1,"author":"Bruno","title":"Aula HTTP","body":"Uma nota para a turma","published":false}
```

```bash
curl -X POST http://127.0.0.1:3000/posts/1/comments \
  -H 'Content-Type: application/json' \
  -d '{"display_name":"Leitor","body":"Como testar?"}'
curl 'http://127.0.0.1:3000/comments?post_id=1'
```

A consulta retorna 200:

```json
{"items":[{"id":1,"post_id":1,"display_name":"Leitor","body":"Como testar?"}],"total":1,"limit":20,"offset":0}
```

IDs são inteiros atribuídos pelo banco e não são reutilizados após exclusão. Os IDs 1 destes exemplos pressupõem banco novo; copie os IDs reais se já houver dados. Para um fluxo sem copiar IDs nem tocar no banco habitual, execute **python examples/demo.py**.

## Rotas

| Método | Rota | Resultado |
|---|---|---|
| GET | /health | 200, status ok |
| GET / POST | /posts | Listagem paginada / criação 201 com Location |
| GET / PATCH / DELETE | /posts/:id | Consultar 200 / editar 200 / excluir 204 |
| GET / POST | /posts/:id/comments | Listar comentários / criar 201 com Location |
| GET | /comments | Listagem paginada de comentários |
| GET / PATCH / DELETE | /comments/:id | Consultar / editar / excluir |

Não há PUT. Crie comentários pela rota aninhada; post_id é atribuído pelo caminho. IDs, post_id e campos desconhecidos não podem ser alterados por PATCH.

```bash
curl -X PATCH http://127.0.0.1:3000/posts/1 \
  -H 'Content-Type: application/json' -d '{"published":true}'
curl -X PATCH http://127.0.0.1:3000/comments/1 \
  -H 'Content-Type: application/json' -d '{"body":"Pergunta revisada"}'
curl -i -X DELETE http://127.0.0.1:3000/posts/1
```

PATCH mantém campos omitidos. Excluir publicação com comentários retorna **409**; nada é excluído em cascata. Remova primeiro os comentários, depois a publicação. Resposta verificada:

```json
{"error":{"code":"has_comments","message":"Remova os comentários antes da publicação."}}
```

## Filtros e paginação

- Publicações: author (igualdade exata), published=true ou false, q (trecho literal em título/corpo).
- Comentários: post_id, q (trecho literal no corpo).
- A rota aninhada também aceita q, limit e offset; pai ausente retorna 404.
- Todas as listagens: limit padrão 20, de 1 a 100; offset padrão 0, de 0 a 100000.
- Ordenação: id crescente. Busca diferencia maiúsculas/minúsculas; % e _ são literais, sem curingas.
- Filtros combinam com AND. q: até 100 caracteres; author: até 80. Parâmetros repetidos, vazios ou desconhecidos retornam 400.
- total conta o conjunto filtrado antes da paginação; items contém a página. Consulta com post_id inexistente na rota plana retorna lista vazia.
- total e página compartilham uma transação de leitura. Entre duas requisições, alterações podem deslocar páginas por offset.

```bash
curl 'http://127.0.0.1:3000/posts?author=Bruno&published=true&limit=10&offset=0'
curl 'http://127.0.0.1:3000/posts/1/comments?q=Como&limit=10'
```

## Validação e erros

| Campo | Regra |
|---|---|
| author / display_name | Texto não vazio, até 80 caracteres |
| title | Texto não vazio, até 160 |
| body | Obrigatório, não vazio; post até 5000, comentário até 2000 |
| published | Booleano real, padrão false |

Textos são aparados; corpo permite nova linha e tabulação, outros controles são rejeitados. published é um marcador, **não uma regra de privacidade**: rascunhos também são consultáveis. Nomes de autor são textos livres, sem conta ou identidade verificada.

| Status | Situação |
|---|---|
| 400 | JSON/UTF-8, filtros ou comprimento do corpo inválido |
| 404 | Recurso/rota ausente |
| 405 | Método não permitido |
| 409 | Publicação ainda tem comentários |
| 413 | Corpo acima de 16 KiB |
| 415 | Corpo sem application/json |
| 422 | Campos/tipos inválidos |
| 503 | Banco indisponível, alteração não confirmada |

Erros seguem `{"error":{"code":"...","message":"..."}}`. Clientes devem enviar Content-Length; Transfer-Encoding não é aceito. Tempo limite de leitura da conexão: 5 s.

## Persistência e limites

Banco padrão: data/notes.sqlite3, ignorado pelo Git. Variáveis: DB_FILE, HOST (127.0.0.1), PORT (3000). Exemplo Bash:

```bash
PORT=3100 DB_FILE=./data/aula.sqlite3 python src/server.py
```

SQLite usa chaves estrangeiras e transações; mutações adquirem bloqueio de escrita, com espera de até 3 s. Erros antes do commit sofrem rollback. Banco corrompido falha na inicialização; preserve o arquivo para recuperação. Não apague o banco para “corrigir” sem backup.

Indicado para estudo e pequenos dados locais. Não há autenticação, autorização, moderação, limite total de registros, quota de disco ou proteção para exposição à internet. O servidor usa a biblioteca http.server de desenvolvimento. Corpo e página têm limites; disco e quantidade de threads dependem do ambiente. Não publique dados pessoais. Use um processo por banco e faça backup com servidor parado. Não há controle de edição obsoleta: a última edição processada de um campo prevalece. Repetir criação gera outro registro; não há idempotência.

## Teste e contribua

```bash
python -m unittest discover -s tests -v
python examples/demo.py
```

Em 06/11/2026: **12 testes aprovados, 0 falhas**, mais demo com asserções. Inclui HTTP real, filtros, concorrência, rollback e reinício. [Comandos e alcance](VERIFICATION.md).

Melhoria concreta: demo isolada e formulário de bug que pede rota, filtros e estado inicial. [Guia de contribuição](CONTRIBUTING.md) · [Relatar falha](https://github.com/perabru/api-lab-2026-11-06/issues/new?template=bug_report.yml). Sugestões de documentação e testes são bem-vindas.

## Referência oficial — consultada em 06/11/2026

[JSONPlaceholder — guia, filtros e recursos aninhados](https://jsonplaceholder.typicode.com/). A documentação informa que criação, edição e exclusão têm respostas simuladas. Este projeto adota um contrato próprio e grava suas operações em SQLite, sem copiar o conjunto de dados, integrar com o provedor ou alegar afiliação. Não implementa todas as rotas do JSONPlaceholder.

## 💛 Incentive a continuidade

![Apoio voluntário por Pix](https://raw.githubusercontent.com/perabru/peradev-apis/main/brand/pix-support.svg)

Se este exemplo ajudou você a aprender, uma colaboração voluntária incentiva a continuidade e novas APIs.

### Copie a chave Pix

```text
bruno.pera@unifesp.br
```

**O apoio é opcional. O código continua aberto e gratuito para todos**, sem promessa de contrapartidas.

## English summary

Local posts and comments API with SQLite persistence, nested resources, combined filters, pagination and guarded deletion. Python standard library only. Twelve HTTP tests passed, including concurrency, rollback and real process restart. Independent study implementation inspired by JSONPlaceholder; no external integration or hosted endpoint.

**Licença MIT · Bruno Michel Pera** · [Calendário](https://github.com/perabru/peradev-apis/blob/main/docs/10-days.md)

[Post bilíngue publicado e verificado no LinkedIn em 06/11/2026](https://www.linkedin.com/feed/update/urn:li:activity:7524412593826951168/).
