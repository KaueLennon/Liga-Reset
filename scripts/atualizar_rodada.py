"""Busca na API do Cartola a pontuação das rodadas encerradas e grava no index.html.

Regras:
- Só busca rodadas já encerradas: a rodada em andamento (rodada_atual da API) nunca é lida,
  porque enquanto ela acontece a API devolve a pontuação da rodada anterior.
- Não regrava rodada que já está salva, a não ser com --forcar.
- Recusa os dados (e falha o workflow, gerando e-mail do GitHub) se vierem incompletos,
  zerados ou iguais aos da rodada anterior.

Uso:
  python scripts/atualizar_rodada.py                 # busca rodadas encerradas que faltam
  python scripts/atualizar_rodada.py --rodada 31 --forcar   # rebusca uma rodada específica
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

API = "https://api.cartola.globo.com"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCO = re.compile(r'(<script id="liga-dados" type="application/json">)(.*?)(</script>)', re.S)
MANUTENCAO = 4


class DadosInvalidos(Exception):
    pass


def get(caminho, tentativas=3):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(API + caminho, headers={"User-Agent": "Mozilla/5.0 (Liga Reset)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            if i == tentativas - 1:
                raise
            time.sleep(5 * (i + 1))


def arred(x):
    return float(Decimal(str(x)).quantize(Decimal("0.01"), ROUND_HALF_UP))


def ler_html(arquivo):
    html = open(arquivo, encoding="utf-8").read()
    m = BLOCO.search(html)
    if not m:
        raise SystemExit("Bloco de dados <script id=\"liga-dados\"> não encontrado em " + arquivo)
    return html, json.loads(m.group(2))


def gravar_html(arquivo, html, dados):
    js = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    novo = BLOCO.sub(lambda m: m.group(1) + js + m.group(3), html, count=1)
    with open(arquivo, "w", encoding="utf-8", newline="\n") as f:
        f.write(novo)


def buscar_rodada(r, times, pont):
    res, inconsistentes = {}, []
    for t in times:
        tid = str(t["id"])
        try:
            j = get(f"/time/id/{tid}/{r}")
        except Exception as e:
            raise DadosInvalidos(f"{t['nome']}: erro ao consultar a API do Cartola ({e})")
        if j.get("rodada_atual") != r:
            raise DadosInvalidos(f"{t['nome']}: a API respondeu a rodada {j.get('rodada_atual')} em vez da {r}")
        if j.get("pontos") is None:
            raise DadosInvalidos(f"{t['nome']}: sem pontuação na rodada {r}")
        res[tid] = arred(j["pontos"])
        # o acumulado do Cartola tem que bater com a soma das rodadas salvas + esta
        anteriores = [pont.get(str(x), {}).get(tid) for x in range(1, r)]
        if j.get("pontos_campeonato") is not None and all(v is not None for v in anteriores):
            if abs(j["pontos_campeonato"] - (sum(anteriores) + j["pontos"])) > 0.5:
                inconsistentes.append(t["nome"])
        time.sleep(0.3)

    if len(res) != len(times):
        raise DadosInvalidos(f"Rodada {r}: vieram {len(res)} de {len(times)} times")
    if all(v == 0 for v in res.values()):
        raise DadosInvalidos(f"Rodada {r}: todas as pontuações vieram zeradas")
    anterior = pont.get(str(r - 1))
    if anterior and sum(1 for k, v in res.items() if anterior.get(k) == v) > len(res) // 2:
        raise DadosInvalidos(f"Rodada {r}: pontuações iguais às da rodada {r - 1} (a rodada ainda não foi consolidada?)")
    if len(inconsistentes) > len(times) // 2:
        raise DadosInvalidos(f"Rodada {r}: acumulado do Cartola não bate para {len(inconsistentes)} times")
    return res, inconsistentes


def resumo(texto):
    print(texto)
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as f:
            f.write(texto + "\n")


def saida(chave, valor):
    destino = os.environ.get("GITHUB_OUTPUT")
    if destino:
        with open(destino, "a", encoding="utf-8") as f:
            f.write(f"{chave}={valor}\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--rodada", type=int, help="rodada específica para buscar")
    ap.add_argument("--forcar", action="store_true", help="regrava a rodada mesmo se já estiver salva")
    ap.add_argument("--arquivo", default=os.path.join(RAIZ, "index.html"))
    a = ap.parse_args()

    html, dados = ler_html(a.arquivo)
    pont = dados.setdefault("pontuacoes", {})
    times = dados["times"]
    saida("mudou", "false")

    st = get("/mercado/status")
    atual, status = st["rodada_atual"], st["status_mercado"]
    total = st.get("rodada_final") or 38
    if status == MANUTENCAO:
        resumo(f"Mercado em manutenção (rodada {atual}). Nada a fazer agora.")
        return 0
    # última rodada encerrada: a anterior à atual, ou a própria atual se a temporada acabou
    ultima = atual if st.get("game_over") else atual - 1
    ultima = min(ultima, total)

    if a.rodada:
        if a.rodada > ultima:
            raise SystemExit(f"A rodada {a.rodada} ainda não terminou (última encerrada: {ultima}).")
        if str(a.rodada) in pont and not a.forcar:
            resumo(f"Rodada {a.rodada} já está salva. Marque 'forcar' para buscar de novo.")
            return 0
        alvos = [a.rodada]
    else:
        alvos = [r for r in range(1, ultima + 1) if str(r) not in pont]

    if not alvos:
        resumo(f"Nada a fazer: última rodada encerrada é a {ultima} e ela já está salva (mercado: rodada {atual}, status {status}).")
        return 0

    feitas = []
    for r in alvos:
        try:
            res, avisos = buscar_rodada(r, times, pont)
        except DadosInvalidos as e:
            resumo(f"❌ {e}")
            if feitas:
                break
            return 1
        pont[str(r)] = res
        feitas.append(r)
        nomes = {str(t["id"]): t["nome"] for t in times}
        top = sorted(res.items(), key=lambda x: -x[1])[:3]
        resumo(f"✅ Rodada {r} salva ({len(res)} times). Destaques: " + ", ".join(f"{nomes[k]} {v:.2f}" for k, v in top))
        if avisos:
            resumo(f"⚠️ Rodada {r}: acumulado do Cartola diferente do salvo para: {', '.join(avisos)} (pode ser correção manual antiga).")

    if not feitas:
        return 1
    dados["atualizadoEm"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    gravar_html(a.arquivo, html, dados)
    saida("mudou", "true")
    saida("rodadas", ",".join(map(str, feitas)))
    return 0 if len(feitas) == len(alvos) else 1


if __name__ == "__main__":
    sys.exit(main())
