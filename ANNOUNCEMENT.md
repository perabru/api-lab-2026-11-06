# Uma conversa que permanece

**Thread Notes API · Dia 04/10 · 06/11/2026**

Uma API local para notas de aula e comentários. Implementei CRUD de publicações e comentários, filtros combinados, paginação e persistência SQLite. Publicações com comentários não podem ser excluídas até a remoção dos filhos.

**Python 3.10+ · sem pacotes externos · 12 testes HTTP aprovados**

```bash
git clone https://github.com/perabru/api-lab-2026-11-06.git
cd api-lab-2026-11-06
python examples/demo.py
python -m unittest discover -s tests -v
python src/server.py
```

[README e exemplos](README.md) · [Código](src/server.py) · [Verificação](VERIFICATION.md) · [Contribuir](CONTRIBUTING.md) · [Post bilíngue](LINKEDIN.md)

A referência [JSONPlaceholder](https://jsonplaceholder.typicode.com/), consultada em 06/11/2026, simula suas alterações. Esta implementação própria grava dados locais em SQLite. Sem integração com o serviço, afiliação ou endpoint hospedado.

A demo isolada verifica criação, consulta e bloqueio de exclusão; o formulário de bug pede filtros e estado inicial. Experimente, envie um caso de borda por issue ou contribua com documentação.

O README destaca apoio voluntário por Pix com a chave bruno.pera@unifesp.br. A contribuição incentiva a continuidade; o código permanece aberto e gratuito.

**English:** A local posts and comments API with nested routes, combined filters, pagination, SQLite persistence and guarded deletion. Twelve HTTP tests passed, including concurrent writes, rollback and real process restart. Explore the isolated demo and suggest a reproducible edge case.

[Post bilíngue publicado e verificado no LinkedIn em 06/11/2026](https://www.linkedin.com/feed/update/urn:li:activity:7524412593826951168/).
