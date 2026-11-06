# Verificação — 06/11/2026

Ambiente Linux, Python 3.12.14, SQLite da biblioteca padrão. Sem instalação de pacotes.

Comandos executados na raiz:
```bash
python -m unittest discover -s tests -v
python examples/demo.py
```

**12 testes aprovados, 0 falhas/erros, exit code 0.** Runner: 6.194 s, duração variável por execução.

1. CRUD de publicação e PATCH que preserva campos.
2. Comentários aninhados equivalentes ao filtro post_id e edição de comentário.
3. Exclusão de pai ocupado bloqueada, sem cascata.
4. Filtros combinados, paginação, ordem estável e busca literal com %.
5. Entradas inválidas e vínculos imutáveis.
6. Filtros inválidos, repetidos e limites.
7. JSON/UTF-8, mídia, tamanho e método HTTP.
8. Pais, recursos e rotas inexistentes.
9. Dezesseis comentários concorrentes, IDs únicos e sem perda.
10. Falha de inserção por trigger SQLite: 503 e nenhum comentário gravado.
11. Banco corrompido rejeitado, preservando bytes.
12. Processo Python real: criar, editar, excluir, terminar e iniciar novamente; posts e comentários idênticos e exclusão mantida.

Demo: exit code 0. POST /posts retornou 201 com id 1 e published false; consulta filtrada retornou um comentário; exclusão do post ocupado retornou 409/has_comments. Respostas completas no README, obtidas nesta execução.

Limites da evidência: rollback induzido por trigger, sem simular disco físico cheio ou perda de energia. Reinício por término de processo; não é teste de carga, Windows, segurança para internet ou serviço hospedado. Não consulta JSONPlaceholder. Paginação por offset em conjunto que muda pode deslocar páginas entre requisições.
