#!/usr/bin/env python3
import http.server
import sqlite3
import json
import os
import uuid
import base64
import hashlib
import hmac
from urllib.parse import urlparse, parse_qs
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'uzy.db')
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
SECRET = 'uzy-modas-secret-2025'
WPP_NUMBER = '559591611196'

os.makedirs(UPLOADS_DIR, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pecas (
        id TEXT PRIMARY KEY,
        nome TEXT NOT NULL,
        descricao TEXT,
        preco REAL NOT NULL,
        preco_original REAL,
        categoria TEXT,
        tamanhos TEXT,
        cor TEXT,
        emoji TEXT,
        imagem TEXT,
        status TEXT DEFAULT 'ativo',
        cliques INTEGER DEFAULT 0,
        criado_em TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS metricas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peca_id TEXT,
        tipo TEXT,
        criado_em TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY,
        senha_hash TEXT
    )''')
    # senha padrão: uzy2025
    senha = hashlib.sha256('uzy2025'.encode()).hexdigest()
    c.execute('INSERT OR IGNORE INTO admin (id, senha_hash) VALUES (1, ?)', (senha,))
    # peças de exemplo
    pecas_exemplo = [
        ('1', 'Vestido Linho Rose', 'Vestido midi em linho com caimento fluido. Perfeito para o dia a dia.', 189.0, None, 'vestido', 'P,M,G', 'rose', '👗', None, 'ativo', 3),
        ('2', 'Blusa Cropped Lilas', 'Blusa cropped em viscolycra com franzido lateral. Levinha e moderna.', 79.0, 110.0, 'blusa', 'PP,P,M', 'lilas', '👚', None, 'ativo', 7),
        ('3', 'Conjunto Alfaiataria', 'Blazer + calça palazzo em tecido de alfaiataria. Elegante e versátil.', 320.0, None, 'conjunto', 'P,M,G,GG', 'preto', '🧥', None, 'ativo', 5),
        ('4', 'Calça Wide Leg', 'Calça wide leg em sarja verde oliva. Confortável e estilosa.', 149.0, None, 'calca', '36,38,40,42', 'verde', '👖', None, 'ativo', 2),
        ('5', 'Vestido Floral', 'Vestido midi estampado floral com manga bufante.', 165.0, 220.0, 'vestido', 'P,M', 'floral', '🌸', None, 'ativo', 9),
    ]
    now = datetime.now().isoformat()
    for p in pecas_exemplo:
        c.execute('INSERT OR IGNORE INTO pecas (id,nome,descricao,preco,preco_original,categoria,tamanhos,cor,emoji,imagem,status,cliques,criado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (*p, now))
    conn.commit()
    conn.close()

def make_token():
    return hashlib.sha256(f'{SECRET}{datetime.now().isoformat()}'.encode()).hexdigest()

TOKENS = set()

def json_response(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', len(body))
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    handler.end_headers()
    handler.wfile.write(body)

def file_response(handler, filepath, content_type='text/html'):
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        handler.send_response(200)
        handler.send_header('Content-Type', content_type)
        handler.send_header('Content-Length', len(content))
        handler.end_headers()
        handler.wfile.write(content)
    except FileNotFoundError:
        handler.send_response(404)
        handler.end_headers()

def check_auth(handler):
    auth = handler.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '')
    return token in TOKENS

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silencia logs verbose

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.end_headers()

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(length) if length else b''

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # Servir arquivos estáticos
        if path == '/' or path == '/index.html':
            file_response(self, os.path.join(os.path.dirname(__file__), 'frontend/public/index.html'))
            return
        if path == '/admin' or path == '/admin.html':
            file_response(self, os.path.join(os.path.dirname(__file__), 'frontend/admin/index.html'))
            return
        if path.startswith('/uploads/'):
            fname = path.replace('/uploads/', '')
            fpath = os.path.join(UPLOADS_DIR, fname)
            ext = fname.split('.')[-1].lower()
            ctype = {'jpg':'image/jpeg','jpeg':'image/jpeg','png':'image/png','webp':'image/webp'}.get(ext,'application/octet-stream')
            file_response(self, fpath, ctype)
            return

        # API
        if path == '/api/pecas':
            conn = get_db()
            cat = qs.get('categoria', [None])[0]
            q = 'SELECT * FROM pecas WHERE status != "arquivado"'
            params = []
            if cat and cat != 'all':
                if cat == 'sale':
                    q += ' AND preco_original IS NOT NULL'
                else:
                    q += ' AND categoria = ?'
                    params.append(cat)
            q += ' ORDER BY criado_em DESC'
            rows = conn.execute(q, params).fetchall()
            conn.close()
            pecas = []
            for r in rows:
                p = dict(r)
                p['tamanhos'] = p['tamanhos'].split(',') if p['tamanhos'] else []
                pecas.append(p)
            json_response(self, pecas)
            return

        if path == '/api/metricas':
            if not check_auth(self):
                json_response(self, {'erro': 'não autorizado'}, 401)
                return
            conn = get_db()
            total = conn.execute('SELECT COUNT(*) as c FROM pecas WHERE status="ativo"').fetchone()['c']
            cliques_hoje = conn.execute(
                "SELECT COUNT(*) as c FROM metricas WHERE tipo='clique' AND criado_em >= date('now')"
            ).fetchone()['c']
            wpp_hoje = conn.execute(
                "SELECT COUNT(*) as c FROM metricas WHERE tipo='whatsapp' AND criado_em >= date('now')"
            ).fetchone()['c']
            mais_vistas = conn.execute(
                'SELECT nome, cliques FROM pecas ORDER BY cliques DESC LIMIT 3'
            ).fetchall()
            conn.close()
            json_response(self, {
                'pecas_ativas': total,
                'cliques_hoje': cliques_hoje,
                'whatsapp_hoje': wpp_hoje,
                'mais_vistas': [dict(r) for r in mais_vistas]
            })
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/login':
            body = json.loads(self.read_body() or b'{}')
            senha = body.get('senha', '')
            senha_hash = hashlib.sha256(senha.encode()).hexdigest()
            conn = get_db()
            admin = conn.execute('SELECT senha_hash FROM admin WHERE id=1').fetchone()
            conn.close()
            if admin and hmac.compare_digest(admin['senha_hash'], senha_hash):
                token = make_token()
                TOKENS.add(token)
                json_response(self, {'token': token, 'ok': True})
            else:
                json_response(self, {'erro': 'senha incorreta'}, 401)
            return

        if path == '/api/clique':
            body = json.loads(self.read_body() or b'{}')
            peca_id = body.get('id')
            tipo = body.get('tipo', 'clique')
            if peca_id:
                conn = get_db()
                conn.execute('UPDATE pecas SET cliques = cliques + 1 WHERE id=?', (peca_id,))
                conn.execute('INSERT INTO metricas (peca_id, tipo, criado_em) VALUES (?,?,?)',
                             (peca_id, tipo, datetime.now().isoformat()))
                conn.commit()
                conn.close()
            json_response(self, {'ok': True})
            return

        if not check_auth(self):
            json_response(self, {'erro': 'não autorizado'}, 401)
            return

        if path == '/api/pecas':
            body = json.loads(self.read_body() or b'{}')
            peca_id = str(uuid.uuid4())[:8]
            tamanhos = ','.join(body.get('tamanhos', []))
            conn = get_db()
            conn.execute('''INSERT INTO pecas (id,nome,descricao,preco,preco_original,categoria,tamanhos,cor,emoji,imagem,status,cliques,criado_em)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?)''',
                (peca_id, body.get('nome',''), body.get('descricao',''),
                 float(body.get('preco',0)), body.get('preco_original') or None,
                 body.get('categoria',''), tamanhos, body.get('cor',''),
                 body.get('emoji','👗'), body.get('imagem'),
                 body.get('status','ativo'), datetime.now().isoformat()))
            conn.commit()
            conn.close()
            json_response(self, {'id': peca_id, 'ok': True})
            return

        if path == '/api/upload':
            ct = self.headers.get('Content-Type','')
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            body = json.loads(raw)
            data_url = body.get('data','')
            if ',' in data_url:
                header, b64 = data_url.split(',', 1)
                ext = 'jpg'
                if 'png' in header: ext = 'png'
                elif 'webp' in header: ext = 'webp'
                fname = f'{uuid.uuid4().hex[:8]}.{ext}'
                fpath = os.path.join(UPLOADS_DIR, fname)
                with open(fpath, 'wb') as f:
                    f.write(base64.b64decode(b64))
                json_response(self, {'url': f'/uploads/{fname}', 'ok': True})
            else:
                json_response(self, {'erro': 'imagem inválida'}, 400)
            return

        self.send_response(404)
        self.end_headers()

    def do_PUT(self):
        if not check_auth(self):
            json_response(self, {'erro': 'não autorizado'}, 401)
            return
        parsed = urlparse(self.path)
        parts = parsed.path.split('/')
        if len(parts) >= 3 and parts[1] == 'api' and parts[2] == 'pecas':
            peca_id = parts[3] if len(parts) > 3 else None
            body = json.loads(self.read_body() or b'{}')
            tamanhos = ','.join(body.get('tamanhos', []))
            conn = get_db()
            conn.execute('''UPDATE pecas SET nome=?,descricao=?,preco=?,preco_original=?,
                categoria=?,tamanhos=?,cor=?,emoji=?,imagem=?,status=? WHERE id=?''',
                (body.get('nome'), body.get('descricao'),
                 float(body.get('preco',0)), body.get('preco_original') or None,
                 body.get('categoria'), tamanhos, body.get('cor'),
                 body.get('emoji'), body.get('imagem'),
                 body.get('status','ativo'), peca_id))
            conn.commit()
            conn.close()
            json_response(self, {'ok': True})
            return
        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        if not check_auth(self):
            json_response(self, {'erro': 'não autorizado'}, 401)
            return
        parts = self.path.split('/')
        if len(parts) >= 4 and parts[1] == 'api' and parts[2] == 'pecas':
            peca_id = parts[3]
            conn = get_db()
            conn.execute("UPDATE pecas SET status='arquivado' WHERE id=?", (peca_id,))
            conn.commit()
            conn.close()
            json_response(self, {'ok': True})
            return
        self.send_response(404)
        self.end_headers()

if __name__ == '__main__':
    init_db()
    PORT = 8765
    server = http.server.HTTPServer(('0.0.0.0', PORT), Handler)
    print(f'✅ Uzy Modas rodando em http://localhost:{PORT}')
    print(f'🛍️  Vitrine: http://localhost:{PORT}/')
    print(f'⚙️  Admin:   http://localhost:{PORT}/admin')
    print(f'🔑 Senha admin: uzy2025')
    server.serve_forever()
