#!/usr/bin/env python3
"""Rebuild the repository table in every profile README.

Lists the owner's public, non-fork, non-archived repositories (the profile
repository itself is skipped) and writes a table between the markers
<!-- REPOS:START --> and <!-- REPOS:END --> in README.md and README/README.<lang>.md.
Descriptions come from data/repo-descriptions.json; a repository without a
translation falls back to its GitHub "About" description.
"""
import json
import os
import pathlib
import re
import urllib.request

OWNER = os.environ.get("PROFILE_OWNER", "jongwooish")
ROOT = pathlib.Path(__file__).resolve().parent.parent
LANGS = ["en", "ko", "ja", "zh-CN", "es", "fr"]
HEAD = {
    "en": ("Repository", "Description", "Language", "Updated"),
    "ko": ("저장소", "설명", "언어", "업데이트"),
    "ja": ("リポジトリ", "説明", "言語", "更新"),
    "zh-CN": ("仓库", "说明", "语言", "更新"),
    "es": ("Repositorio", "Descripción", "Lenguaje", "Actualizado"),
    "fr": ("Dépôt", "Description", "Langage", "Mis à jour"),
}
EMPTY = {"en": "No public repositories yet.", "ko": "아직 공개 저장소가 없습니다.", "ja": "公開リポジトリはまだありません。",
         "zh-CN": "暂无公开仓库。", "es": "Todavía no hay repositorios públicos.", "fr": "Aucun dépôt public pour l'instant."}
START, END = "<!-- REPOS:START -->", "<!-- REPOS:END -->"


def fetch_repos():
    if os.environ.get("REPOS_JSON"):
        return json.loads(pathlib.Path(os.environ["REPOS_JSON"]).read_text(encoding="utf-8"))
    repos, page = [], 1
    while True:
        url = f"https://api.github.com/users/{OWNER}/repos?type=owner&per_page=100&page={page}"
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-updater"})
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req) as r:
            batch = json.load(r)
        repos += batch
        if len(batch) < 100:
            return repos
        page += 1


def cell(s):
    return (s or "").replace("|", "\\|").replace("\n", " ").strip()


def table(repos, lang, desc):
    if not repos:
        return EMPTY[lang]
    h = HEAD[lang]
    rows = [f"| {h[0]} | {h[1]} | {h[2]} | {h[3]} |", "| --- | --- | --- | --- |"]
    for r in repos:
        d = desc.get(r["name"]) or {k.lower(): v for k, v in desc.items()}.get(r["name"].lower(), {})
        text = d.get(lang) or d.get("en") or r.get("description") or "—"
        rows.append(f"| [{r['name']}]({r['html_url']}) | {cell(text)} | {r.get('language') or '—'} | {r['pushed_at'][:10]} |")
    return "\n".join(rows)


def main():
    desc = json.loads((ROOT / "data" / "repo-descriptions.json").read_text(encoding="utf-8"))
    repos = [r for r in fetch_repos()
             if not r.get("private") and not r.get("fork") and not r.get("archived")
             and r["name"].lower() != OWNER.lower()]
    repos.sort(key=lambda r: r["pushed_at"], reverse=True)
    pat = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    for lang in LANGS:
        path = ROOT / "README.md" if lang == "en" else ROOT / "README" / f"README.{lang}.md"
        text = path.read_text(encoding="utf-8")
        new = pat.sub(f"{START}\n{table(repos, lang, desc)}\n{END}", text)
        if new != text:
            path.write_text(new, encoding="utf-8")
            print("updated", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
