"""Thread Notes: local posts and comments, Python standard library only."""
import json
import os
from pathlib import Path
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class ApiError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


def fail(status, code, message):
    raise ApiError(status, code, message)


def connect(path):
    db = sqlite3.connect(path, timeout=3)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        version = db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1):
            raise RuntimeError('Versão de banco não suportada.')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS posts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          author TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
          published INTEGER NOT NULL CHECK(published IN (0,1)));
        CREATE TABLE IF NOT EXISTS comments (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE RESTRICT,
          display_name TEXT NOT NULL, body TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS comments_post ON comments(post_id, id);
        PRAGMA user_version = 1;
        ''')
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('Banco inconsistente; preserve o arquivo para recuperação.')


def fields(data, kind, patch=False):
    limits = {'author': 80, 'title': 160, 'body': 5000} if kind == 'posts' else {'display_name': 80, 'body': 2000}
    allowed = set(limits) | ({'published'} if kind == 'posts' else set())
    required = set(limits)
    if not isinstance(data, dict) or not data or set(data) - allowed or (not patch and not required <= set(data)):
        fail(422, 'validation_error', 'Objeto vazio, campos desconhecidos ou obrigatórios ausentes.')
    out = {}
    for key, value in data.items():
        if key == 'published':
            if type(value) is not bool:
                fail(422, 'validation_error', 'published deve ser booleano.')
            out[key] = int(value)
        else:
            # Body allows newlines and tabs; names/titles stay on one line.
            pattern = r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]' if key == 'body' else r'[\x00-\x1f\x7f]'
            if not isinstance(value, str) or not value.strip() or len(value) > limits[key] or re.search(pattern, value):
                fail(422, 'validation_error', f'{key}: texto não vazio, máximo {limits[key]}.')
            out[key] = value.strip()
    if kind == 'posts' and not patch:
        out.setdefault('published', 0)
    return out


def view(row, kind):
    result = dict(row)
    if kind == 'posts':
        result['published'] = bool(result['published'])
    return result


def make_server(path, host='127.0.0.1', port=3000):
    initialize(path)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'ThreadNotes/1.0'

        def log_message(self, *args):
            pass  # Never log request bodies or user content.

        def reply(self, status, data=None, headers=None):
            encoded = b'' if data is None else json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            for k, v in {'Content-Type': 'application/json; charset=utf-8', 'Content-Length': str(len(encoded)), 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', **(headers or {})}.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(encoded)

        def read_body(self):
            if self.headers.get('Transfer-Encoding'):
                fail(400, 'invalid_body', 'Transfer-Encoding não suportado; envie Content-Length.')
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                fail(415, 'unsupported_media_type', 'Use application/json.')
            length = self.headers.get('Content-Length', '')
            if not re.fullmatch(r'[0-9]+', length) or len(length) > 8:
                fail(400, 'invalid_body', 'Content-Length inválido ou ausente.')
            size = int(length)
            if size > 16384:
                fail(413, 'payload_too_large', 'Máximo 16 KiB.')
            try:
                raw = self.rfile.read(size)
                if len(raw) != size:
                    fail(400, 'invalid_body', 'Corpo incompleto.')
                return json.loads(raw.decode('utf-8'))
            except (ValueError, UnicodeError):
                fail(400, 'invalid_json', 'JSON UTF-8 inválido.')

        def run(self):
            db = None
            try:
                self.connection.settimeout(5)
                url = urlsplit(self.path)
                if url.path == '/health' and self.command == 'GET' and not url.query:
                    return self.reply(200, {'status': 'ok'})
                match = re.fullmatch(r'/(posts|comments)(?:/([1-9][0-9]{0,14}))?(?:/(comments))?', url.path)
                if not match or (match[3] and (match[1] != 'posts' or not match[2])):
                    fail(404, 'not_found', 'Rota não encontrada.')
                kind, ident, nested = match.groups()
                allowed = ['GET', 'POST'] if not ident or nested else ['GET', 'PATCH', 'DELETE']
                if self.command not in allowed:
                    return self.reply(405, {'error': {'code': 'method_not_allowed', 'message': 'Método não permitido.'}}, {'Allow': ', '.join(allowed)})
                if kind == 'comments' and not ident and self.command == 'POST':
                    fail(405, 'method_not_allowed', 'Crie comentários em /posts/:id/comments.')
                query = parse_qs(url.query, keep_blank_values=True)
                list_route = self.command == 'GET' and (not ident or nested)
                permitted = {'limit', 'offset', 'q'} | ({'author', 'published'} if kind == 'posts' and not nested else ({'post_id'} if not nested else set()))
                if (query and not list_route) or set(query) - permitted or any(len(v) != 1 or not v[0] for v in query.values()):
                    fail(400, 'invalid_query', 'Filtros desconhecidos, repetidos ou vazios.')
                query = {k: v[0] for k, v in query.items()}
                data = self.read_body() if self.command in ('POST', 'PATCH') else None
                db = connect(path)
                if self.command != 'GET':
                    db.execute('BEGIN IMMEDIATE')
                if ident:
                    row = db.execute(f'SELECT * FROM {kind} WHERE id=?', (int(ident),)).fetchone()
                    if row is None:
                        fail(404, 'not_found', 'Recurso não encontrado.')
                resource = 'comments' if nested else kind
                if list_route:
                    params, clauses = [], []
                    def clause(sql, val):
                        clauses.append(sql)
                        params.append(val)
                    if nested:
                        clause('post_id=?', int(ident))
                    if 'post_id' in query:
                        if not re.fullmatch(r'[1-9][0-9]{0,14}', query['post_id']):
                            fail(400, 'invalid_query', 'post_id inválido.')
                        clause('post_id=?', int(query['post_id']))
                    if 'author' in query:
                        if len(query['author']) > 80:
                            fail(400, 'invalid_query', 'author muito longo.')
                        clause('author=?', query['author'])
                    if 'published' in query:
                        if query['published'] not in ('true', 'false'):
                            fail(400, 'invalid_query', 'published: use true ou false.')
                        clause('published=?', int(query['published'] == 'true'))
                    if 'q' in query:
                        if len(query['q']) > 100:
                            fail(400, 'invalid_query', 'q: máximo 100 caracteres.')
                        # instr treats % and _ literally; deterministic case-sensitive search.
                        target = "title || char(10) || body" if resource == 'posts' else 'body'
                        clause(f'instr({target}, ?) > 0', query['q'])
                    def number(key, default, maximum):
                        val = query.get(key, str(default))
                        if not re.fullmatch(r'[0-9]{1,6}', val) or int(val) > maximum or (key == 'limit' and int(val) == 0):
                            fail(400, 'invalid_query', f'{key} inválido.')
                        return int(val)
                    limit, offset = number('limit', 20, 100), number('offset', 0, 100000)
                    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
                    db.execute('BEGIN')  # count + page share one snapshot.
                    total = db.execute(f'SELECT count(*) FROM {resource}{where}', params).fetchone()[0]
                    items = db.execute(f'SELECT * FROM {resource}{where} ORDER BY id ASC LIMIT ? OFFSET ?', params + [limit, offset]).fetchall()
                    return self.reply(200, {'items': [view(r, resource) for r in items], 'total': total, 'limit': limit, 'offset': offset})
                if self.command == 'GET':
                    return self.reply(200, view(row, resource))
                if self.command == 'POST':
                    values = fields(data, resource)
                    if nested:
                        values['post_id'] = int(ident)
                    cols = list(values)
                    cursor = db.execute(f'INSERT INTO {resource} ({",".join(cols)}) VALUES ({",".join("?" for _ in cols)})', list(values.values()))
                    result = view(db.execute(f'SELECT * FROM {resource} WHERE id=?', (cursor.lastrowid,)).fetchone(), resource)
                    db.commit()
                    return self.reply(201, result, {'Location': f'/{resource}/{result["id"]}'})
                if self.command == 'PATCH':
                    values = fields(data, resource, True)
                    db.execute(f'UPDATE {resource} SET {",".join(k+"=?" for k in values)} WHERE id=?', [*values.values(), int(ident)])
                    result = view(db.execute(f'SELECT * FROM {resource} WHERE id=?', (int(ident),)).fetchone(), resource)
                    db.commit()
                    return self.reply(200, result)
                if resource == 'posts' and db.execute('SELECT 1 FROM comments WHERE post_id=?', (int(ident),)).fetchone():
                    fail(409, 'has_comments', 'Remova os comentários antes da publicação.')
                db.execute(f'DELETE FROM {resource} WHERE id=?', (int(ident),))
                db.commit()
                self.reply(204)
            except ApiError as e:
                self.reply(e.status, {'error': {'code': e.code, 'message': e.message}})
            except sqlite3.Error:
                self.reply(503, {'error': {'code': 'storage_unavailable', 'message': 'Banco indisponível; alteração não confirmada.'}})
            except (TimeoutError, ConnectionError):
                pass
            except Exception:
                self.reply(500, {'error': {'code': 'internal_error', 'message': 'Erro interno.'}})
            finally:
                if db is not None:
                    db.close()  # uncommitted transactions roll back.

        do_GET = do_POST = do_PATCH = do_DELETE = do_PUT = do_OPTIONS = do_HEAD = run

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server


if __name__ == '__main__':
    server = make_server(os.environ.get('DB_FILE', 'data/notes.sqlite3'), os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '3000')))
    print(f'Thread Notes API: http://{server.server_address[0]}:{server.server_address[1]}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
