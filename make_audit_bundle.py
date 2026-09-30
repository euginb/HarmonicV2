from pathlib import Path
import subprocess

ROOT = Path(".").resolve()
OUT = ROOT / "AUDIT_BUNDLE.md"

TEXT_EXT = {
    ".md", ".py", ".json", ".toml", ".yaml", ".yml", ".txt",
    ".cfg", ".ini", ".j2", ".jinja", ".jinja2", ".csv", ".tsv",
    ".svg",
}

MAX_FILE_BYTES = 300_000

def run(cmd):
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()

head = run(["git", "rev-parse", "HEAD"])
files = run(["git", "ls-files"]).splitlines()

with OUT.open("w", encoding="utf-8", newline="\n") as out:
    out.write("# AUDIT BUNDLE HarmonicV2\n\n")
    out.write(f"HEAD: `{head}`\n\n")

    out.write("## Git tree\n\n")
    out.write("```text\n")
    for f in files:
        out.write(f + "\n")
    out.write("```\n\n")

    out.write("Примечание: Файлы в репозитории ссылаются на 'docs/HG-Series-Catalog_opt.pdf', но в самом репозитории его нет. Это не ошибка. Он исключен намеренно с целью уменьшить размер данного файла\n\n")

    out.write("## Text file contents\n\n")

    for rel in files:
        path = ROOT / rel
        ext = path.suffix.lower()

        if ext not in TEXT_EXT:
            continue

        try:
            size = path.stat().st_size
        except OSError:
            continue

        if size > MAX_FILE_BYTES:
            out.write(f"\n---\n\n")
            out.write(f"### FILE: `{rel}`\n\n")
            out.write(f"Skipped: file is too large, {size} bytes.\n")
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        out.write(f"\n---\n\n")
        out.write(f"### FILE: `{rel}`\n\n")
        out.write("```text\n")
        out.write(text)
        if not text.endswith("\n"):
            out.write("\n")
        out.write("```\n")

print(f"Wrote {OUT}")
