# LinkedIn — Thread Notes API

- Estado: publicado e verificado em 06/11/2026.
- Perfil: https://www.linkedin.com/in/brunopera00/
- Permalink: https://www.linkedin.com/feed/update/urn:li:activity:7524412593826951168/
- Autorização diária de 04/11/2026, válida para este desafio até 12/11/2026.
- Prevenção de duplicatas: manifesto e LINKEDIN.md sem registro do dia; atividades recentes mostravam Board Lane (05/11), Order Once (04/11) e Project Shelf (03/11), sem Thread Notes. Publicar acionado uma única vez.
- Evidência: “Publicação concluída.”; permalink aberto com texto português e inglês visível e cartão do repositório correto. A captura de screenshot expirou, sem afetar a confirmação do conteúdo.
- Código confirmado antes do envio: https://github.com/perabru/api-lab-2026-11-06/commit/0fb95b2fe56b61218d08498d151689398694b5bd
- Texto de origem: 2010 caracteres.

## Texto

🇧🇷 Uma resposta 201 basta para provar que um dado foi salvo?

No dia 4 de “10 APIs em 10 dias”, publiquei a Thread Notes API: publicações e comentários para notas de aula ou pequenos projetos.

Implementei criação, consulta, edição e exclusão, comentários por publicação, filtros combináveis e paginação. Os dados são gravados em SQLite; excluir uma publicação com comentários retorna conflito, evitando apagar a conversa sem querer.

A referência foi o JSONPlaceholder, cuja documentação explica que as alterações são simuladas. Aqui, o contrato é próprio e a persistência é local, sem integração externa.

Aprendizado: testar a resposta HTTP e depois reiniciar o processo ajuda a verificar se a gravação realmente permaneceu.

12 testes HTTP passaram, cobrindo vínculos, entradas inválidas, concorrência, rollback e reinício real. Python e SQLite, sem pacotes externos. Código para execução local; sem endpoint hospedado.

🇬🇧 Is a 201 response enough to prove data was saved?

For day 4 of “10 APIs in 10 days”, I built Thread Notes API: posts and comments for class notes or small projects.

It supports CRUD, nested comments, combined filters and pagination. Data is stored in SQLite. Deleting a post that still has comments returns a conflict to protect the conversation.

JSONPlaceholder was the study reference; its docs explain that write operations are simulated. This independent API stores its own data locally, without external integration.

My takeaway: checking the HTTP response and then restarting the process provides stronger evidence that data persisted.

All 12 HTTP tests passed, covering relationships, invalid input, concurrency, rollback and a real restart. Python and SQLite, no third-party packages. Local execution; no hosted endpoint.

Código e exemplos / Code and examples:
https://github.com/perabru/api-lab-2026-11-06

Qual regra você acrescentaria para proteger os comentários?
What rule would you add to protect comments? Feedback welcome!

#API #Python #SQLite #OpenSource
