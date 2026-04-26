"""
NextDNS API Connection Test
Testa a conectividade e autenticação com a API do NextDNS.

Uso:
    python test_nextdns.py
"""

import urllib.request
import json
import ssl

# ─────────────────────────────────────────────
#  CONFIGURAÇÃO — preencha com seus dados
# ─────────────────────────────────────────────
CONFIG_ID = "SEU_CONFIG_ID"   # Encontrado em: app.nextdns.io → Setup
API_KEY   = "SUA_API_KEY"     # Encontrado em: app.nextdns.io → Account → API
# ─────────────────────────────────────────────

URL = f"https://api.nextdns.io/profiles/{CONFIG_ID}/denylist"

print("=" * 50)
print("  NextDNS API — Teste de Conexão")
print("=" * 50)
print(f"\nConfig ID : {CONFIG_ID}")
print(f"URL       : {URL}\n")

if CONFIG_ID == "SEU_CONFIG_ID" or API_KEY == "SUA_API_KEY":
    print("❌ Preencha CONFIG_ID e API_KEY antes de executar.")
    input("\nPressione Enter para fechar...")
    exit(1)

# Testa adicionando um domínio inofensivo de exemplo
TEST_DOMAIN = "example-block-test.com"
data = json.dumps({"id": TEST_DOMAIN, "active": True}).encode()

req = urllib.request.Request(URL, data=data, method="POST")
req.add_header("X-Api-Key", API_KEY)
req.add_header("Content-Type", "application/json")
req.add_header(
    "User-Agent",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)

try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(f"✅ SUCESSO! Status: {r.status}")
        print(f"   Domínio '{TEST_DOMAIN}' adicionado à denylist.")
        print("\n   Suas credenciais estão corretas e a API está acessível.")
except urllib.error.HTTPError as e:
    body = e.read().decode(errors="ignore")
    print(f"❌ Erro HTTP {e.code}: {body}")
    if e.code == 401:
        print("   → API Key inválida ou incorreta.")
    elif e.code == 403:
        print("   → Acesso negado. Verifique sua API Key e Config ID.")
    elif e.code == 404:
        print("   → Config ID não encontrado.")
    elif e.code == 409:
        print(f"✅ Domínio '{TEST_DOMAIN}' já existe na denylist — conexão OK!")
except urllib.error.URLError as e:
    print(f"❌ Erro de rede: {e.reason}")
except ssl.SSLError as e:
    print(f"❌ Erro SSL: {e}")
except Exception as e:
    print(f"❌ Erro inesperado: {type(e).__name__}: {e}")

input("\nPressione Enter para fechar...")
