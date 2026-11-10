"""Prototype (M0): an OpenStax book repository checkout -> the library folder contract
(source.json + document.json). Licence and chapter order come from the book's own metadata."""
import json, re, subprocess, sys
import xml.etree.ElementTree as ET
from pathlib import Path

COL = "{http://cnx.rice.edu/collxml}"
MD = "{http://cnx.rice.edu/mdml}"
CNX = "{http://cnx.rice.edu/cnxml}"
LICENCES = {"by/4.0": "CC BY 4.0", "by-sa/4.0": "CC BY-SA 4.0", "by-nc-sa/4.0": "CC BY-NC-SA 4.0",
            "by-nc/4.0": "CC BY-NC 4.0", "by-nd/4.0": "CC BY-ND 4.0", "by-nc-nd/4.0": "CC BY-NC-ND 4.0"}


def licence(url: str) -> str:
    m = re.search(r"licenses/([a-z-]+/\d\.\d)", url)
    if not m or m.group(1) not in LICENCES:
        raise SystemExit(f"unknown licence: {url!r}")
    name = LICENCES[m.group(1)]
    if "ND" in name:
        raise SystemExit(f"no-derivatives licence rejected: {name}")
    return name


def text_of(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def blocks_of(module: Path, chapter_no: int, chapter: str, base: str):
    doc = ET.parse(module).getroot()
    page = text_of(doc.find(f"{CNX}title"))
    content = doc.find(f"{CNX}content")
    out, objectives = [], []

    def emit(section, sid, kind, parts):
        text = "\n\n".join(p for p in parts if p)
        if text:
            out.append({"chapter_no": chapter_no, "chapter": chapter, "section": section, "kind": kind,
                        "text": text, "source_uri": base + (f"#{sid}" if sid else "")})

    def walk(node, section, sid):
        parts = []
        for child in node:
            tag = child.tag.replace(CNX, "")
            if tag == "section":
                emit(section, sid, "text", parts); parts = []
                t = child.find(f"{CNX}title")
                name = text_of(t) if t is not None else section
                sub = walk(child, f"{page}: {name}", child.get("id"))
                if name.lower().startswith("learning objective"):
                    objectives.extend(l[2:] for s in sub for l in s.split("\n") if l.startswith("- "))
                emit(f"{page}: {name}", child.get("id"), "text", sub)
            elif tag == "title":
                continue
            elif tag == "code" and child.get("display") == "block":
                parts.append("```\n" + "".join(child.itertext()).strip("\n") + "\n```")
            elif tag == "list":
                parts.append("\n".join("- " + text_of(i) for i in child.findall(f"{CNX}item")))
            elif tag == "table":
                rows = [" | ".join(text_of(e) for e in r.iter(f"{CNX}entry")) for r in child.iter(f"{CNX}row")]
                parts.append("\n".join(rows))
            else:
                parts.append(text_of(child))
        return parts

    emit(page, None, "text", walk(content, page, None))
    glossary = doc.find(f"{CNX}glossary")
    if glossary is not None:
        terms = [f"**{text_of(d.find(f'{CNX}term'))}:** {text_of(d.find(f'{CNX}meaning'))}"
                 for d in glossary.findall(f"{CNX}definition")]
        emit(f"{page}: Glossary", None, "glossary", terms)
    return out, page, objectives


def main(repo_dir: str, repo: str, out_dir: str) -> None:
    root = Path(repo_dir)
    sha = subprocess.run(["git", "-C", repo_dir, "rev-parse", "HEAD"], capture_output=True, text=True,
                         check=True).stdout.strip()
    for col_path in sorted(root.glob("collections/*.collection.xml")):
        col = ET.parse(col_path).getroot()
        meta = col.find(f"{COL}metadata")
        title, slug = meta.find(f"{MD}title").text, meta.find(f"{MD}slug").text
        lic = licence(meta.find(f"{MD}license").get("url"))
        blocks, chapters, missing, outline = [], 0, [], []
        for sub in col.find(f"{COL}content").findall(f"{COL}subcollection"):
            chapters += 1
            chapter = sub.find(f"{MD}title").text
            outline.append({"chapter_no": chapters, "chapter": chapter, "pages": []})
            for mod in sub.iter(f"{COL}module"):
                mid = mod.get("document")
                path = root / "modules" / mid / "index.cnxml"
                if not path.exists():
                    missing.append(mid); continue
                base = f"https://github.com/openstax/{repo}/blob/{sha}/modules/{mid}/index.cnxml"
                got, page, objectives = blocks_of(path, chapters, chapter, base)
                blocks += got
                outline[-1]["pages"].append({"module": mid, "title": page, "objectives": objectives, "source_uri": base})
        out = Path(out_dir) / slug
        out.mkdir(parents=True, exist_ok=True)
        (out / "source.json").write_text(json.dumps({
            "subject_slug": slug, "subject_name_vi": title, "subject_name_en": title, "title": title,
            "author": "OpenStax", "license": lic, "url": f"https://openstax.org/details/books/{slug}",
            "version": sha}, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "document.json").write_text(json.dumps({"blocks": blocks}, ensure_ascii=False), encoding="utf-8")
        (out / "outline.json").write_text(json.dumps({"chapters": outline}, ensure_ascii=False, indent=1), encoding="utf-8")
        kinds = {}
        for b in blocks:
            kinds[b["kind"]] = kinds.get(b["kind"], 0) + 1
        print(json.dumps({"book": slug, "title": title, "license": lic, "commit": sha[:8], "chapters": chapters,
                          "blocks": len(blocks), "kinds": kinds, "chars": sum(len(b["text"]) for b in blocks),
                          "objectives": sum(len(p["objectives"]) for c in outline for p in c["pages"]), "missing_modules": missing}, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:4])
