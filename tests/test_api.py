import concurrent.futures
import http.client
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from server import make_server, initialize


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / 'notes.sqlite3')
        self.server = make_server(self.db, port=0)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def req(self, method, path, data=None, raw=None, content_type='application/json'):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=6)
        body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
        conn.request(method, path, body, {'Content-Type': content_type})
        r = conn.getresponse()
        payload = r.read()
        result = (r.status, json.loads(payload) if payload else None, dict(r.getheaders()))
        conn.close()
        return result

    def post(self, **kwargs):
        s, p, h = self.req('POST', '/posts', {'author': 'Bruno', 'title': 'Aula HTTP', 'body': 'Texto original', **kwargs})
        self.assertEqual(s, 201)
        self.assertEqual(h['Location'], '/posts/' + str(p['id']))
        return p

    def comment(self, pid):
        s, c, _ = self.req('POST', f'/posts/{pid}/comments', {'display_name': 'Leitor', 'body': 'Uma pergunta'})
        self.assertEqual(s, 201)
        return c

    def test_post_crud_and_patch_preserves_fields(self):
        p = self.post()
        self.assertFalse(p['published'])
        s, new, _ = self.req('PATCH', f'/posts/{p["id"]}', {'published': True})
        self.assertEqual(s, 200)
        self.assertEqual(new, {**p, 'published': True})
        self.assertEqual(self.req('GET', '/posts/1')[1], new)
        self.assertEqual(self.req('DELETE', '/posts/1')[:2], (204, None))
        self.assertEqual(self.req('GET', '/posts/1')[0], 404)

    def test_nested_and_filtered_comments_equivalent(self):
        p, other = self.post(), self.post()
        c = self.comment(p['id'])
        self.comment(other['id'])
        a = self.req('GET', '/posts/1/comments')[1]
        self.assertEqual(a, self.req('GET', '/comments?post_id=1')[1])
        self.assertEqual(a['items'], [c])
        self.assertEqual(self.req('PATCH', '/comments/1', {'body': 'Revisado'})[1]['body'], 'Revisado')

    def test_delete_parent_guard_no_cascade(self):
        self.post()
        self.comment(1)
        self.assertEqual(self.req('DELETE', '/posts/1')[0], 409)
        self.assertEqual(self.req('GET', '/comments/1')[0], 200)
        self.assertEqual(self.req('DELETE', '/comments/1')[0], 204)
        self.assertEqual(self.req('DELETE', '/posts/1')[0], 204)

    def test_filters_pagination_and_literal_search(self):
        self.post(title='100% APIs', published=True)
        self.post(title='100 APIs', author='Outro')
        self.post(title='100% APIs', published=True)
        result = self.req('GET', '/posts?author=Bruno&published=true&q=%25&limit=1&offset=1')[1]
        self.assertEqual((result['total'], result['limit'], result['offset']), (2, 1, 1))
        self.assertEqual(result['items'][0]['id'], 3)
        self.assertEqual(self.req('GET', '/posts?q=apis')[1]['total'], 0)
        self.assertEqual(self.req('GET', '/posts?offset=90')[1]['items'], [])

    def test_invalid_fields_and_immutable_relationship(self):
        for data in [{}, [], None, {'author': 'X'}, {'author': 'X', 'title': 'Y', 'body': 'Z', 'published': 1}]:
            self.assertEqual(self.req('POST', '/posts', raw=json.dumps(data).encode())[0], 422)
        self.post()
        for patch in [{'title': ''}, {'id': 2}, {'body': None}, {'author': 'x\nY'}, {'title': 'x' * 161}]:
            self.assertEqual(self.req('PATCH', '/posts/1', patch)[0], 422)
        self.comment(1)
        self.assertEqual(self.req('PATCH', '/comments/1', {'post_id': 2})[0], 422)
        self.assertEqual(self.req('GET', '/posts/1')[1]['title'], 'Aula HTTP')

    def test_invalid_query_parameters(self):
        self.post()
        for q in ['limit=0', 'limit=101', 'offset=-1', 'offset=100001', 'q=', 'q=a&q=b', 'x=1', 'published=1', 'post_id=1']:
            self.assertEqual(self.req('GET', '/posts?' + q)[0], 400, q)
        self.assertEqual(self.req('GET', '/comments?post_id=x')[0], 400)
        self.assertEqual(self.req('GET', '/posts/1?q=x')[0], 400)

    def test_http_errors_media_json_size_methods(self):
        self.assertEqual(self.req('GET', '/health')[:2], (200, {'status': 'ok'}))
        for raw, mime, status in [(b'{', 'application/json', 400), (b'\xff', 'application/json', 400), (b'{}', 'text/plain', 415), (b'x' * 16385, 'application/json', 413)]:
            s, body, _ = self.req('POST', '/posts', raw=raw, content_type=mime)
            self.assertEqual(s, status)
            self.assertIn('code', body['error'])
        s, _, h = self.req('PUT', '/posts')
        self.assertEqual(s, 405)
        self.assertEqual(h['Allow'], 'GET, POST')

    def test_missing_parent_and_resources(self):
        self.assertEqual(self.req('POST', '/posts/999/comments', {'display_name': 'X', 'body': 'Y'})[0], 404)
        self.assertEqual(self.req('GET', '/posts/999/comments')[0], 404)
        for path in ['/missing', '/posts/0', '/posts/1/nope', '/comments/999']:
            self.assertEqual(self.req('GET', path)[0], 404)
        self.assertEqual(self.req('GET', '/comments?post_id=999')[1]['total'], 0)

    def test_concurrent_comments_no_loss(self):
        self.post()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            comments = list(pool.map(lambda _: self.comment(1), range(16)))
        self.assertEqual(len({c['id'] for c in comments}), 16)
        self.assertEqual(self.req('GET', '/posts/1/comments')[1]['total'], 16)

    def test_storage_failure_rolls_back(self):
        self.post()
        db = sqlite3.connect(self.db)
        db.execute("CREATE TRIGGER reject_comment BEFORE INSERT ON comments BEGIN SELECT RAISE(ABORT, 'disk failure simulation'); END")
        db.commit()
        self.assertEqual(self.req('POST', '/posts/1/comments', {'display_name': 'X', 'body': 'Y'})[0], 503)
        self.assertEqual(self.req('GET', '/comments')[1]['total'], 0)
        db.close()

    def test_corrupt_database_preserved(self):
        corrupt = Path(self.tmp.name) / 'corrupt.sqlite3'
        corrupt.write_bytes(b'not a database')
        with self.assertRaises(sqlite3.DatabaseError):
            initialize(str(corrupt))
        self.assertEqual(corrupt.read_bytes(), b'not a database')

    def test_real_process_restart_preserves_edits_and_deletion(self):
        db = str(Path(self.tmp.name) / 'restart.sqlite3')
        env = {**os.environ, 'PORT': '0', 'DB_FILE': db}
        def launch():
            p = subprocess.Popen([sys.executable, '-u', 'src/server.py'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            line = p.stdout.readline().strip()
            self.assertIn('Thread Notes API:', line)
            self.port = int(line.rsplit(':', 1)[1])
            return p
        def stop(p):
            p.terminate()
            p.communicate(timeout=5)
        p = launch()
        try:
            self.post()
            self.comment(1)
            self.req('PATCH', '/posts/1', {'published': True})
            self.req('PATCH', '/comments/1', {'body': 'Persistiu'})
            self.post(title='Excluir')
            self.req('DELETE', '/posts/2')
            before = [self.req('GET', x)[1] for x in ['/posts', '/comments']]
        finally:
            stop(p)
        p = launch()
        try:
            self.assertEqual(before, [self.req('GET', x)[1] for x in ['/posts', '/comments']])
            self.assertEqual(self.req('GET', '/posts/2')[0], 404)
        finally:
            stop(p)


if __name__ == '__main__':
    unittest.main(verbosity=2)
