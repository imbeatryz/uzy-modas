# 🛍️ Uzy Modas — SaaS de Vitrine Digital

## Como rodar

### 1. Instale o Python (já vem no Windows/Mac/Linux)

### 2. Inicie o servidor
```bash
cd uzy-modas
python3 server.py
```

### 3. Acesse
- **Vitrine pública** (para clientes): http://localhost:8765/
- **Painel admin** (para a lojista): http://localhost:8765/admin
- **Senha padrão do admin**: `uzy2025`

---

## Funcionalidades

### Vitrine pública
- ✅ Catálogo com foto, preço, tamanhos
- ✅ Filtros por categoria (vestidos, blusas, conjuntos, calças, promoções)
- ✅ Modal de detalhes com seleção de tamanho
- ✅ Botão WhatsApp com mensagem automática personalizada
- ✅ Contador de cliques (rastreamento de interesse)
- ✅ Design elegante e responsivo

### Painel Admin
- ✅ Login com senha
- ✅ Dashboard com métricas (peças ativas, cliques hoje, contatos WhatsApp, taxa de conversão)
- ✅ Peças mais visualizadas
- ✅ Cadastrar/editar/remover peças
- ✅ Upload de fotos
- ✅ Marcar como esgotado

---

## Para publicar na internet (deixar acessível 24h)

Opções gratuitas/baratas:
- **Railway.app** — fácil, ~$5/mês
- **Render.com** — grátis com limitações
- **VPS DigitalOcean** — ~$6/mês, controle total

---

## Estrutura do projeto
```
uzy-modas/
├── server.py          ← Backend (API + servidor de arquivos)
├── uzy.db             ← Banco de dados SQLite (criado automaticamente)
├── uploads/           ← Fotos das peças
└── frontend/
    ├── public/        ← Vitrine para clientes
    │   └── index.html
    └── admin/         ← Painel da lojista
        └── index.html
```

---

## Alterar senha do admin
No terminal:
```python
python3 -c "
import sqlite3, hashlib
conn = sqlite3.connect('uzy.db')
nova = hashlib.sha256('NOVA_SENHA'.encode()).hexdigest()
conn.execute('UPDATE admin SET senha_hash=? WHERE id=1', (nova,))
conn.commit()
print('Senha alterada!')
"
```
