"""Assemble the static files published by GitHub Pages."""

from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import ROOT

SITE = ROOT / "_pages_site"
STATIC_SOURCE = ROOT / "static"


def main():
    SITE.mkdir(exist_ok=True)
    (SITE / "static").mkdir(exist_ok=True)
    (SITE / "data").mkdir(exist_ok=True)

    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    html = html.replace('<html lang="id">', '<html lang="id" data-static-mode="true">')
    html = html.replace('href="/static/', 'href="static/')
    html = html.replace('src="/static/', 'src="static/')
    html = html.replace("Saldo tersimpan di perangkat/server ini.", "Dompet demo tersimpan di browser ini.")
    html = html.replace("Saldo tersimpan di perangkat/server ini", "Dompet demo tersimpan di browser ini")
    (SITE / "index.html").write_text(html, encoding="utf-8")

    for source in STATIC_SOURCE.iterdir():
        if source.is_file():
            shutil.copy2(source, SITE / "static" / source.name)
    shutil.copy2(ROOT / "data" / "market.json", SITE / "data" / "market.json")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built GitHub Pages site in {SITE}")


if __name__ == "__main__":
    main()
