"""
NextDNS Blocklist Importer
Importa listas de domínios para o NextDNS via API.

Uso:
    python import_nextdns.py

Dependências:
    - Python 3.7+
    - aiohttp (instalado automaticamente na primeira execução)
"""

import subprocess
import sys

try:
    import aiohttp
except ImportError:
    print("Instalando aiohttp...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp", "-q"])
    import aiohttp

import asyncio
import time
import os

# ─────────────────────────────────────────────
#  CONFIGURAÇÃO — preencha com seus dados
# ─────────────────────────────────────────────
CONFIG_ID = "SEU_CONFIG_ID"   # Encontrado em: app.nextdns.io → Setup
API_KEY   = "SUA_API_KEY"     # Encontrado em: app.nextdns.io → Account → API
# ─────────────────────────────────────────────

BASE_URL = f"https://api.nextdns.io/profiles/{CONFIG_ID}/denylist"
HEADERS  = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Número de workers simultâneos.
# ⚠️  A API do NextDNS limita a ~1-2 requisições/s por chave.
# Aumentar este valor além de 8-10 causará muitos erros por rate limit.
WORKERS = 8

# Listas a importar — adicione ou remova conforme necessário.
# Caminhos relativos ao diretório do script.
LISTS = [
    ("NSFW / Adulto", os.path.join(os.path.dirname(__file__), "lists", "nsfw_domains.txt")),
    # ("Malware",      os.path.join(os.path.dirname(__file__), "lists", "malware.txt")),
]


def parse_domain(line: str) -> str | None:
    """
    Aceita dois formatos de lista:
      - Formato AdBlock:  ||dominio.com^
      - Formato simples:  dominio.com
    Linhas em branco e comentários (#) são ignorados.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("||") and line.endswith("^"):
        return line[2:-1]
    return line


async def worker(session, queue, stats, goal, start):
    while True:
        try:
            domain = queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        try:
            async with session.post(
                BASE_URL,
                json={"id": domain, "active": True},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status in (200, 201, 204):
                    stats["ok"] += 1
                elif r.status == 409:
                    stats["skip"] += 1  # já existe na lista
                elif r.status == 429:
                    # Rate limit — devolve à fila e aguarda
                    await queue.put(domain)
                    await asyncio.sleep(2)
                    queue.task_done()
                    continue
                else:
                    stats["err"] += 1
        except Exception:
            stats["err"] += 1

        stats["total"] += 1
        queue.task_done()

        n = stats["total"]
        if n % 500 == 0 or n == goal:
            elapsed = time.time() - start
            rate = n / elapsed if elapsed > 0 else 1
            remaining = (goal - n) / rate
            print(
                f'  {n:>7}/{goal:,} ({n/goal*100:.1f}%) | '
                f'OK: {stats["ok"]:>6} | '
                f'Skip: {stats["skip"]:>5} | '
                f'Err: {stats["err"]:>5} | '
                f'{rate:.1f} req/s | '
                f'~{remaining/60:.1f}min restantes'
            )


async def import_list(filepath: str, label: str):
    if not os.path.exists(filepath):
        print(f"\n[AVISO] Arquivo não encontrado: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        domains = [d for line in f if (d := parse_domain(line))]

    print(f'\n{"=" * 70}')
    print(f"  {label}: {len(domains):,} domínios | {WORKERS} workers")
    print(f'{"=" * 70}')

    stats = {"ok": 0, "skip": 0, "err": 0, "total": 0}
    start = time.time()

    queue = asyncio.Queue()
    for d in domains:
        await queue.put(d)

    connector = aiohttp.TCPConnector(limit=WORKERS, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        tasks = [
            asyncio.create_task(worker(session, queue, stats, len(domains), start))
            for _ in range(WORKERS)
        ]
        await asyncio.gather(*tasks)

    elapsed = time.time() - start
    ok_pct = stats["ok"] / len(domains) * 100 if domains else 0
    print(
        f'\n  Concluído em {elapsed / 60:.1f} min | '
        f'OK: {stats["ok"]:,} ({ok_pct:.0f}%) | '
        f'Skip: {stats["skip"]:,} | '
        f'Err: {stats["err"]:,}'
    )


async def main():
    if CONFIG_ID == "SEU_CONFIG_ID" or API_KEY == "SUA_API_KEY":
        print("❌ Configure CONFIG_ID e API_KEY no início do script antes de executar.")
        input("Pressione Enter para fechar...")
        return

    print("=" * 70)
    print("  NextDNS Blocklist Importer")
    print(f"  Config ID: {CONFIG_ID}")
    print("=" * 70)

    for label, filepath in LISTS:
        await import_list(filepath, label)

    print("\n\nTudo pronto! Verifique em app.nextdns.io → Denylist.")
    input("\nPressione Enter para fechar...")


asyncio.run(main())
