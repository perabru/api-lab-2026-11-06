"""Isolated HTTP demo with assertions; no installed packages or persistent data."""
import json
from pathlib import Path
import sys
import tempfile
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from server import make_server

with tempfile.TemporaryDirectory() as tmp:
    server = make_server(str(Path(tmp) / 'demo.sqlite3'), port=0)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    def call(method, path, data=None):
        req = Request(f'http://127.0.0.1:{server.server_port}{path}', method=method,
                      data=json.dumps(data).encode() if data is not None else None,
                      headers={'Content-Type': 'application/json'})
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    try:
        status, post = call('POST', '/posts', {'author': 'Bruno', 'title': 'Aula HTTP', 'body': 'Uma nota para a turma'})
        assert status == 201 and post == {'id': 1, 'author': 'Bruno', 'title': 'Aula HTTP', 'body': 'Uma nota para a turma', 'published': False}
        print('POST /posts -> 201', json.dumps(post, ensure_ascii=False))
        status, comment = call('POST', '/posts/1/comments', {'display_name': 'Leitor', 'body': 'Como testar?'})
        assert status == 201 and comment['post_id'] == 1
        status, result = call('GET', '/comments?post_id=1')
        assert status == 200 and result == {'items': [comment], 'total': 1, 'limit': 20, 'offset': 0}
        print('GET /comments?post_id=1 -> 200', json.dumps(result, ensure_ascii=False))
        status, error = call('DELETE', '/posts/1')
        assert status == 409 and error['error']['code'] == 'has_comments'
        print('DELETE /posts/1 -> 409', json.dumps(error, ensure_ascii=False))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
