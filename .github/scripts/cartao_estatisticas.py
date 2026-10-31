"""Gera o cartão "Estatísticas do GitHub" (SVG) com a API GraphQL do GitHub.

Substitui o github-readme-stats.vercel.app, cuja instância pública saiu do ar
(DEPLOYMENT_PAUSED). Roda no workflow do Pac-Man e publica no branch output.

Uso: GITHUB_TOKEN=... python cartao_estatisticas.py <usuario> <arquivo.svg>
"""
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

CONSULTA = """
query($login: String!, $depois: String) {
  user(login: $login) {
    name
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar { totalContributions }
    }
    repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    repositories(first: 100, after: $depois, ownerAffiliations: OWNER, isFork: false) {
      nodes { stargazerCount }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

FUNDO = "#0B1B2E"
TITULO = "#FF8A3D"
ICONE = "#4C9AFF"
TEXTO = "#E6EDF3"


def consultar(token, login, depois=None):
    corpo = json.dumps({"query": CONSULTA, "variables": {"login": login, "depois": depois}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=corpo,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        dados = json.load(r)
    if dados.get("errors"):
        raise SystemExit(f"Erro na API do GitHub: {dados['errors']}")
    return dados["data"]["user"]


def numeros(token, login):
    user = consultar(token, login)
    estrelas = 0
    repos = user["repositories"]
    while True:
        estrelas += sum(n["stargazerCount"] for n in repos["nodes"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        repos = consultar(token, login, repos["pageInfo"]["endCursor"])["repositories"]
    c = user["contributionsCollection"]
    return {
        "nome": user["name"] or login,
        "contribuicoes": c["contributionCalendar"]["totalContributions"],
        "commits": c["totalCommitContributions"],
        "privadas": c["restrictedContributionsCount"],
        "prs": c["totalPullRequestContributions"],
        "issues": c["totalIssueContributions"],
        "repos": user["repositoriesContributedTo"]["totalCount"],
        "estrelas": estrelas,
    }


def svg(n):
    linhas = [
        ("Contribuições (12 meses)", n["contribuicoes"]),
        ("Commits (12 meses)", n["commits"]),
        ("Contribuições privadas", n["privadas"]),
        ("Pull requests", n["prs"]),
        ("Issues", n["issues"]),
        ("Repositórios em que contribuiu", n["repos"]),
    ]
    altura = 58 + 22 * len(linhas) + 8
    itens = []
    for i, (rotulo, valor) in enumerate(linhas):
        y = 58 + 22 * i
        valor = f"{valor:,}".replace(",", ".")
        itens.append(
            f'<circle cx="31" cy="{y - 4}" r="4" fill="{ICONE}"/>'
            f'<text x="44" y="{y}" class="r">{escape(rotulo)}:</text>'
            f'<text x="375" y="{y}" class="v" text-anchor="end">{valor}</text>'
        )
    titulo = escape(f"Estatísticas de {n['nome']} no GitHub")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="{altura}" viewBox="0 0 400 {altura}" '
        f'role="img" aria-label="{titulo}">'
        f"<style>.t{{font:600 17px 'Segoe UI',Ubuntu,Sans-Serif;fill:{TITULO}}}"
        f".r{{font:400 13px 'Segoe UI',Ubuntu,Sans-Serif;fill:{TEXTO}}}"
        f".v{{font:700 13px 'Segoe UI',Ubuntu,Sans-Serif;fill:{TEXTO}}}</style>"
        f'<rect width="400" height="{altura}" rx="12" fill="{FUNDO}"/>'
        f'<text x="25" y="32" class="t">{titulo}</text>'
        + "".join(itens)
        + "</svg>"
    )


def main():
    login, saida = sys.argv[1], sys.argv[2]
    token = os.environ["GITHUB_TOKEN"]
    n = numeros(token, login)
    os.makedirs(os.path.dirname(saida) or ".", exist_ok=True)
    with open(saida, "w", encoding="utf-8") as f:
        f.write(svg(n))
    print({k: v for k, v in n.items() if k != "nome"})


if __name__ == "__main__":
    main()
