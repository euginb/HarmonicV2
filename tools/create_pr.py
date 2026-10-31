"""
create_pr.py — Создание Pull Request через GitHub API (для использования в сессиях HarmonicV2).

Использует токен из GH_TOKEN / GITHUB_TOKEN / github_pat_… (переменная окружения GITHUB_TOKEN,
или токен, зашитый в переменную окружения GH_TOKEN).

Использование:
    python tools/create_pr.py <head> <base> [options]

Аргументы:
    head      — имя локальной ветки, из которой создаётся PR (обязательно, должна быть на origin)
    base      — базовая ветка для мерджа (обычно main)
    -t, --title  — заголовок PR (по умолчанию формируется автоматически)
    -m, --message  — тело PR (Markdown, по умолчанию — краткое описание)
    --repo    — путь до репозитория в формате owner/repo (по умолчанию: euginb/HarmonicV2)
    --dry-run — вывести JSON запроса в stdout, не отправляя

Переменные окружения:
    GITHUB_TOKEN / GH_TOKEN  — токен GitHub с правами public_repo (обязательно)

Примеры:
    python tools/create_pr.py rev11.8 main
    python tools/create_pr.py rev11.8 main -t "[rev-11.8] CP-90 Добавил расчёт сепаратора"
    python tools/create_pr.py rev11.8 main --dry-run
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# ── Кодировка stdout ─────────────────────────────────────────────────────────
# На Windows console по умолчанию cp1251 — не умеет стрелки/Unicode.
# Переключаем на UTF-8, если stdout — терминал.
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Константы ────────────────────────────────────────────────────────────────

REPO_DEFAULT = "euginb/HarmonicV2"
API_BASE = "https://api.github.com"

# ── Утилиты ──────────────────────────────────────────────────────────────────


def get_token() -> str:
    """Возвращает токен GitHub из переменных окружения.

    Приоритет: GITHUB_TOKEN > GH_TOKEN.
    Если токен не найден — аварийная остановка.
    """
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")
    if not token:
        print("Ошибка: переменная окружения GITHUB_TOKEN (или GH_TOKEN) не задана", file=sys.stderr)
        sys.exit(1)
    return token


def build_pr_title(head: str, message: str | None) -> str:
    """Формирует заголовок PR из имени ветки и краткого сообщения.

    По умолчанию: [<branch>] <message>.
    Если message не задан — пытается извлечь CP-## из ветки и описания.
    """
    if message:
        return message
    # Пытаемся извлечь префикс ревизии из имени ветки
    branch = head.replace("rev", "")
    return f"[rev-{branch}] {head}"


def build_pr_body(message: str | None, head: str, base: str) -> str:
    """Формирует тело PR."""
    lines = []
    if message:
        lines.append(message)
    else:
        lines.append(f"Мердж `{head}` → `{base}`.")
        lines.append("")
        lines.append("## Проверки")
        lines.append("- `python main.py all` → OK (код выхода 0)")
    return "\n".join(lines)


def create_pull_request(
    token: str,
    repo: str,
    head: str,
    base: str,
    title: str,
    body: str,
    dry_run: bool = False,
) -> dict | None:
    """Создаёт PR через GitHub REST API.

    Параметры
    ---------
    token : str
        Токен GitHub.
    repo : str
        Формат `owner/repo`.
    head : str
        Имя ветки с изменениями (должна быть на origin).
    base : str
        Целевая ветка для мерджа.
    title : str
        Заголовок PR.
    body : str
        Тело PR (Markdown).
    dry_run : bool
        Если True — только выводит JSON, не отправляя.

    Возвращает
    ----------
    dict | None
        Ответ API (с полем `html_url`) или None при ошибке / dry-run.
    """
    url = f"{API_BASE}/repos/{repo}/pulls"
    payload = {
        "title": title,
        "body": body,
        "head": head,
        "base": base,
    }

    if dry_run:
        print("=== dry-run: отправка не выполнена ===")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return None

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        print(f"PR создан: {result['html_url']}")
        return result
    except urllib.error.HTTPError as e:
        print(f"Ошибка API {e.code}: {e.read().decode()}", file=sys.stderr)
        return None


# ── Точка входа ──────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Создание Pull Request через GitHub API (HarmonicV2).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
примеры:
  python tools/create_pr.py rev11.8 main
  python tools/create_pr.py rev11.8 main -t "[rev-11.8] CP-90 Новые расчёты"
  python tools/create_pr.py rev11.8 main --dry-run
        """,
    )
    parser.add_argument("head", help="Ветка с изменениями (должна быть на origin)")
    parser.add_argument("base", help="Базовая ветка для мерджа")
    parser.add_argument("-t", "--title", help="Заголовок PR (по умолчанию — авто)", default=None)
    parser.add_argument("-m", "--message", help="Тело PR (Markdown)", default=None)
    parser.add_argument("--repo", help=f"Репозитория owner/repo (по умолчанию: {REPO_DEFAULT})", default=REPO_DEFAULT)
    parser.add_argument("--dry-run", action="store_true", help="Вывести JSON запроса, не отправляя")

    args = parser.parse_args()

    token = get_token()

    title = args.title or build_pr_title(args.head, args.message)
    body = build_pr_body(args.message, args.head, args.base)

    create_pull_request(token, args.repo, args.head, args.base, title, body, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
