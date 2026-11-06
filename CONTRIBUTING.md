# Contribua com um caso reproduzível

Use Python 3.10+ e rode:
```bash
python -m unittest discover -s tests -v
python examples/demo.py
```

A demo cria um banco temporário e verifica as respostas; não altera seu banco habitual. Para relatar problemas, use o formulário de bug com rota, filtros, estado inicial e resultado esperado. Use dados fictícios e remova conteúdo pessoal.

Mudanças de filtros devem incluir um teste HTTP com filtros combinados, paginação e entradas inválidas. Mudanças na gravação devem verificar reinício e ausência de órfãos. Não inclua data/, bancos, logs ou segredos. Abra issue/PR no próprio projeto; documentação e correções pequenas são bem-vindas.

Código MIT, aberto e gratuito. Apoio voluntário pelo Pix bruno.pera@unifesp.br incentiva a continuidade, sem contrapartidas.
