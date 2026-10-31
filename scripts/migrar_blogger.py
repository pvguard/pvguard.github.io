#!/usr/bin/env python3
"""
migrar_blogger.py - Pasa todos los posts de un blog de Blogger a este sitio Jekyll.

Conserva el HTML original de cada post (con sus estilos), las etiquetas, el
"leer mas" (<!--more-->) y las URLs (/AAAA/MM/slug.html). Descarga las imagenes
a assets/img/posts/<slug>/ para no depender de Blogger.

Uso (desde la raiz del repo):

    # Opcion A - leer el blog publico directamente
    python3 scripts/migrar_blogger.py

    # Opcion B - usar la copia de seguridad de Blogger (fechas exactas)
    #   Blogger > Configuracion > Administrar blog > Hacer copia de seguridad del contenido
    python3 scripts/migrar_blogger.py --xml blog-AAAA-MM-DD.xml

Opciones:
    --blog URL         Blog de origen (por defecto https://pvguard.blogspot.com)
    --sin-imagenes     No descarga imagenes (las deja apuntando a Blogger)
    --sobrescribir     Reemplaza posts que ya existan en _posts/
    --solo-listar      Muestra lo que haria sin escribir nada

Solo usa la libreria estandar de Python 3.8+.
"""

import argparse
import html
import json
import mimetypes
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "_posts")
DRAFTS_DIR = os.path.join(ROOT, "_drafts")
IMG_DIR = os.path.join(ROOT, "assets", "img", "posts")
LABEL_DIR = os.path.join(ROOT, "search", "label")
CONFIG = os.path.join(ROOT, "_config.yml")

IMG_URL_RE = re.compile(
    r"https?://(?:blogger\.googleusercontent\.com/img/[^\s\"'()<>]+"
    r"|\d\.bp\.blogspot\.com/[^\s\"'()<>]+)")


# ----------------------------------------------------------------- red
def fetch(url, binary=False, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
                ctype = r.headers.get("Content-Type", "")
                return (data, ctype) if binary else data.decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"No se pudo descargar {url}: {last}")


# ----------------------------------------------------------------- HTML
class BloggerPage(HTMLParser):
    """Extrae titulo, etiquetas, cuerpo y enlaces de una pagina de Blogger."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.title_parts, self.labels, self.post_links = [], [], []
        self.older = None
        self.meta = {}
        self._in_title = self._in_labels = self._in_label_a = self._in_list_title = False
        self._body_start = None
        self._body_depth = 0
        self._body_range = None
        self._labels_depth = 0
        self._raw = ""

    def feed_text(self, text):
        self._raw = text
        self._lines = [0]
        for m in re.finditer("\n", text):
            self._lines.append(m.end())
        self.feed(text)
        self.close()

    def _offset(self):
        line, col = self.getpos()
        return self._lines[line - 1] + col

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "meta":
            k = a.get("property") or a.get("name")
            if k:
                self.meta[k] = a.get("content", "")
        if tag == "h3" and "post-title" in cls:
            self._in_title = True
            self.title_parts = []
        if tag == "a" and self._in_title:
            if a.get("href"):
                self.post_links.append(a["href"])
        if tag == "a" and "blog-pager-older-link" in cls:
            self.older = a.get("href")
        if tag == "span" and "post-labels" in cls:
            self._in_labels = True
        if tag == "a" and self._in_labels:
            self._in_label_a = True
            self.labels.append("")
        if tag == "div":
            if self._body_start is None and self._body_range is None and "post-body" in cls:
                start = self._offset()
                end_of_tag = self._raw.index(">", start) + 1
                self._body_start = end_of_tag
                self._body_depth = 1
            elif self._body_start is not None:
                self._body_depth += 1

    def handle_startendtag(self, tag, attrs):
        if tag == "meta":
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "h3" and self._in_title:
            self._in_title = False
        if tag == "a" and self._in_label_a:
            self._in_label_a = False
        if tag == "span" and self._in_labels:
            self._in_labels = False
        if tag == "div" and self._body_start is not None:
            self._body_depth -= 1
            if self._body_depth == 0:
                self._body_range = (self._body_start, self._offset())
                self._body_start = None

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        if self._in_label_a and self.labels:
            self.labels[-1] += data

    @property
    def title(self):
        return html.unescape(" ".join("".join(self.title_parts).split()))

    @property
    def body(self):
        if not self._body_range:
            return None
        s, e = self._body_range
        return self._raw[s:e]


def parse_page(text):
    p = BloggerPage()
    p.feed_text(text)
    return p


# --------------------------------------------------------------- origenes
def from_blog(blog, skip=()):
    """Recorre la portada y la paginacion para listar los posts (del mas nuevo al mas viejo)."""
    blog = blog.rstrip("/")
    urls, seen, page, guard = [], set(), blog + "/", 0
    while page and guard < 50:
        guard += 1
        print(f"  indice: {page}")
        p = parse_page(fetch(page))
        for u in p.post_links:
            u = u.split("#")[0].split("?")[0]
            if u.startswith(blog) and u.endswith(".html") and u not in seen:
                seen.add(u)
                urls.append(u)
        page = html.unescape(p.older) if p.older else None

    # Blogger no publica el dia exacto: se asigna un dia por mes respetando el orden original
    urls = [u for u in urls if re.search(r"/\d{4}/\d{2}/[^/]+\.html$", u)]
    by_month = defaultdict(list)
    for u in urls:
        y, mo = re.search(r"/(\d{4})/(\d{2})/", u).groups()
        by_month[(int(y), int(mo))].append(u)
    dates = {}
    for (y, mo), group in by_month.items():
        n = len(group)
        for i, u in enumerate(group):
            dates[u] = f"{y:04d}-{mo:02d}-{max(1, min(28, n - i)):02d} 12:00:00 -0500"

    posts = []
    for u in urls:
        m = re.search(r"/(\d{4})/(\d{2})/([^/]+)\.html$", u)
        base = {"url": u, "year": int(m.group(1)), "month": int(m.group(2)), "slug": m.group(3),
                "date": dates[u], "labels": [], "body": "", "image": "", "description": "",
                "title": m.group(3)}
        if u in skip:
            posts.append(base)
            continue
        print(f"  post: {u}")
        try:
            p = parse_page(fetch(u))
        except RuntimeError as err:
            print(f"    ! {err}")
            continue
        if p.body is None:
            print("    ! no se encontro .post-body, se omite")
            continue
        base.update({
            "title": p.title or m.group(3), "labels": [l.strip() for l in p.labels if l.strip()],
            "body": p.body, "image": p.meta.get("og:image", ""),
            "description": p.meta.get("og:description", ""),
        })
        posts.append(base)
    return posts


def to_local_date(iso, tz_offset="-05:00"):
    """Convierte una fecha ISO (UTC) a la hora de Lima para que el orden y el mes coincidan con Blogger."""
    from datetime import datetime, timedelta, timezone
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    sign = -1 if tz_offset.startswith("-") else 1
    hh, mm = tz_offset[1:].split(":")
    tz = timezone(sign * timedelta(hours=int(hh), minutes=int(mm)))
    return d.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S %z")


def plain_description(body, limit=155):
    """Primer texto del post (sin el titulo en <h1>) para la meta descripcion."""
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", body)
    text = re.sub(r"(?is)<h1\b.*?</h1>", " ", text, count=1)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def from_xml(path, blog):
    """Lee la copia de seguridad de Blogger (.xml clasico o feed.atom de Google Takeout)."""
    A = "{http://www.w3.org/2005/Atom}"
    B = "{http://schemas.google.com/blogger/2018}"
    blog = blog.rstrip("/")
    tree = ET.parse(path)
    posts = []
    for e in tree.getroot().findall(A + "entry"):
        cats = e.findall(A + "category")
        kinds = [c.get("term", "") for c in cats if c.get("scheme", "").endswith("#kind")]
        btype = (e.findtext(B + "type") or "").strip()
        if not (btype == "POST" or any(k.endswith("#post") for k in kinds)):
            continue  # comentarios, paginas, ajustes...
        if (e.findtext(B + "trashed") or "").strip():
            continue
        status = (e.findtext(B + "status") or "").strip()
        draft = status in ("DRAFT", "SCHEDULED") or e.find("{http://purl.org/atom/app#}control") is not None
        if status and status not in ("LIVE", "DRAFT", "SCHEDULED"):
            continue

        link = None
        for l in e.findall(A + "link"):
            if l.get("rel") == "alternate":
                link = l.get("href")
        filename = (e.findtext(B + "filename") or "").strip()
        if not link and filename:
            link = blog + filename if filename.startswith("/") else filename
        m = re.search(r"/(\d{4})/(\d{2})/([^/]+)\.html$", link or "")
        if not m:
            continue

        labels = [c.get("term") for c in cats
                  if not c.get("scheme", "").endswith("#kind") and c.get("term")]
        published = (e.findtext(A + "published") or e.findtext(A + "updated") or "").strip()
        try:
            date = to_local_date(published) if published else None
        except ValueError:
            date = None
        if not date:
            date = f"{m.group(1)}-{m.group(2)}-01 12:00:00 -0500"
        content = e.findtext(A + "content") or ""
        first_img = IMG_URL_RE.search(content)
        desc = (e.findtext(B + "metaDescription") or "").strip() or plain_description(content)
        posts.append({
            "url": link, "year": int(m.group(1)), "month": int(m.group(2)), "slug": m.group(3),
            "permalink": urllib.parse.urlparse(link).path,
            "title": " ".join((e.findtext(A + "title") or m.group(3)).split()),
            "labels": labels, "body": content, "image": first_img.group(0) if first_img else "",
            "description": desc, "date": date, "draft": draft,
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


# ---------------------------------------------------------------- imagenes
def image_key(url):
    """Misma imagen en distintos tamanos -> misma clave."""
    u = re.sub(r"/[swh]\d+(?:-[a-z0-9-]+)?/(?=[^/]+$)", "/", url)
    u = re.sub(r"=[swh]\d+[^/]*$", "", u)
    return u


def size_score(url):
    m = re.search(r"/s(\d+)/[^/]+$", url) or re.search(r"=s(\d+)", url)
    if m:
        return int(m.group(1))
    if re.search(r"/img/a/[^/=]+$", url):
        return 10 ** 6  # original sin redimensionar
    return 0


def localize_images(post, dry=False):
    urls = set(IMG_URL_RE.findall(post["body"]))
    if post["image"]:
        urls.add(post["image"])
    if not urls:
        return
    groups = defaultdict(list)
    for u in urls:
        groups[image_key(html.unescape(u))].append(u)

    folder = os.path.join(IMG_DIR, post["slug"] + f"-{post['year']}{post['month']:02d}")
    web_folder = "/assets/img/posts/" + os.path.basename(folder)
    mapping = {}
    for n, (key, variants) in enumerate(sorted(groups.items()), 1):
        best = max(variants, key=lambda v: size_score(html.unescape(v)))
        src = html.unescape(best)
        base = urllib.parse.unquote(src.rstrip("/").split("/")[-1].split("=")[0])
        base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-")[:60] or "imagen"
        if dry:
            local = f"{web_folder}/{n:02d}-{base}"
        else:
            try:
                data, ctype = fetch(src, binary=True)
            except RuntimeError as err:
                print(f"    ! {err}")
                continue
            ext = os.path.splitext(base)[1].lower()
            if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
                ext = mimetypes.guess_extension((ctype or "").split(";")[0].strip()) or ".img"
                ext = ".jpg" if ext == ".jpe" else ext
                base = os.path.splitext(base)[0] + ext
            os.makedirs(folder, exist_ok=True)
            name = f"{n:02d}-{base}"
            with open(os.path.join(folder, name), "wb") as fh:
                fh.write(data)
            local = f"{web_folder}/{name}"
        for v in variants:
            mapping[v] = local

    for old in sorted(mapping, key=len, reverse=True):
        post["body"] = post["body"].replace(old, mapping[old])
    if post["image"] in mapping:
        post["image"] = mapping[post["image"]]
    print(f"    imagenes: {len(set(mapping.values()))}")


# ------------------------------------------------------------------ salida
def post_files():
    for folder in (POSTS_DIR, DRAFTS_DIR):
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder)):
                if name.endswith((".html", ".md")):
                    yield os.path.join(folder, name)


def existing_sources():
    found = {}
    for path in post_files():
        try:
            head = open(path, encoding="utf-8").read(2000)
        except OSError:
            continue
        m = re.search(r'^blogger_url:\s*"?([^"\n]+)"?', head, re.M)
        if m:
            found[m.group(1).strip()] = path
    return found


def raw_block(text):
    text = text.replace("{% endraw %}", "{% endraw %}{{ '{% endraw %}' }}{% raw %}")
    return "{% raw %}" + text + "{% endraw %}"


LINKED_LABELS = set()


def rewrite_internal_links(body, blog):
    """Cambia los enlaces al blog viejo por rutas del sitio nuevo."""
    host = re.escape(urllib.parse.urlparse(blog).netloc)

    def label(m):
        name = urllib.parse.unquote_plus(html.unescape(m.group(1)))
        LINKED_LABELS.add(name)
        return f"/search/label/{slugify(name)}/"

    body = re.sub(r"https?://" + host + r"/search/label/([^\"'?#<>\s]+)(?:\?[^\"'#<>\s]*)?", label, body)
    body = re.sub(r"https?://" + host + r"(/\d{4}/\d{2}/[^\"'?#<>\s]+\.html)", r"\1", body)
    body = re.sub(r"https?://" + host + r"/?(?=[\"'])", "/", body)
    return body


def write_post(post, overwrite, existing, dry, blog="https://pvguard.blogspot.com"):
    if post["url"] and post["url"] in existing:
        if not overwrite:
            print(f"    = ya existe ({os.path.basename(existing[post['url']])}), se conserva")
            return False
        if not dry:
            os.remove(existing[post["url"]])

    body = rewrite_internal_links(post["body"].strip(), blog)
    # Restos del editor de Blogger: enlaces vacios a "goog_123..."
    body = re.sub(r"<a href=\"goog_\d+\">(.*?)</a>", r"\1", body, flags=re.S)
    body = re.sub(r"(?:<span>\s*)?<a\s+name=['\"]more['\"]\s*>\s*</a>(?:\s*</span>)?", "<!--more-->", body, count=1)
    if "<!--more-->" in body:
        before, after = body.split("<!--more-->", 1)
        content = raw_block(before) + "\n<!--more-->\n" + raw_block(after)
    else:
        content = raw_block(body)

    fm = ["---",
          f"title: {json.dumps(post['title'], ensure_ascii=False)}",
          f"date: {post['date']}",
          f"tags: {json.dumps(post['labels'], ensure_ascii=False)}"]
    if post["description"]:
        fm.append(f"description: {json.dumps(post['description'], ensure_ascii=False)}")
    if post["image"]:
        fm.append(f"image: {json.dumps(post['image'])}")
    if post.get("permalink"):
        fm.append(f"permalink: {json.dumps(post['permalink'])}")
    if post["url"]:
        fm.append(f"blogger_url: {json.dumps(post['url'])}")
    fm.append("---")

    day = post["date"][:10]
    if post.get("draft"):
        folder, name = DRAFTS_DIR, f"{post['slug']}.html"
    else:
        folder, name = POSTS_DIR, f"{day}-{post['slug']}.html"
    path = os.path.join(folder, name)
    if dry:
        print(f"    -> {os.path.relpath(path, ROOT)}")
        return True
    os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(fm) + "\n" + content + "\n")
    print(f"    -> {os.path.relpath(path, ROOT)}")
    return True


def localize_existing(dry):
    """Descarga las imagenes de Blogger de los posts ya migrados y reescribe sus rutas."""
    print("[*] Buscando imagenes de Blogger en _posts/ y _drafts/ ...")
    for path in post_files():
        text = open(path, encoding="utf-8").read()
        if not IMG_URL_RE.search(text):
            continue
        name = os.path.splitext(os.path.basename(path))[0]
        m = re.match(r"(\d{4})-(\d{2})-\d{2}-(.+)$", name)
        if m:
            year, month, slug = int(m.group(1)), int(m.group(2)), m.group(3)
        else:
            d = re.search(r"^date:\s*(\d{4})-(\d{2})", text, re.M)
            year, month, slug = (int(d.group(1)), int(d.group(2)), name) if d else (0, 0, name)
        print(f"[+] {os.path.relpath(path, ROOT)}")
        post = {"slug": slug, "year": year, "month": month, "body": text, "image": ""}
        localize_images(post, dry=dry)
        if not dry and post["body"] != text:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(post["body"])


def slugify(label):
    s = label.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def ensure_label_pages(labels, dry):
    os.makedirs(LABEL_DIR, exist_ok=True)
    for label in sorted(labels):
        slug = slugify(label)
        path = os.path.join(LABEL_DIR, slug + ".html")
        if os.path.exists(path) or not slug:
            continue
        print(f"  nueva seccion: /search/label/{slug}/")
        if not dry:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(f"---\nlayout: label\ntitle: {json.dumps(label)}\nlabel: {json.dumps(label)}\n"
                         f"permalink: /search/label/{slug}/\n---\n")


def localize_logo(dry):
    try:
        cfg = open(CONFIG, encoding="utf-8").read()
    except OSError:
        return
    m = re.search(r'^logo:\s*"(https?://[^"]+)"', cfg, re.M)
    if not m:
        return
    print("  logo de la cabecera")
    if dry:
        return
    try:
        data, _ = fetch(m.group(1), binary=True)
    except RuntimeError as err:
        print(f"    ! {err}")
        return
    os.makedirs(os.path.join(ROOT, "assets", "img"), exist_ok=True)
    with open(os.path.join(ROOT, "assets", "img", "logo.png"), "wb") as fh:
        fh.write(data)
    cfg = cfg.replace(m.group(0), 'logo: "/assets/img/logo.png"')
    with open(CONFIG, "w", encoding="utf-8") as fh:
        fh.write(cfg)


def main():
    ap = argparse.ArgumentParser(description="Migra un blog de Blogger a este sitio Jekyll.")
    ap.add_argument("--blog", default="https://pvguard.blogspot.com")
    ap.add_argument("--xml", help="Archivo .xml exportado desde Blogger")
    ap.add_argument("--sin-imagenes", action="store_true")
    ap.add_argument("--sobrescribir", action="store_true")
    ap.add_argument("--solo-listar", action="store_true")
    ap.add_argument("--solo-imagenes", action="store_true",
                    help="Descarga las imagenes de Blogger de los posts que ya estan en _posts/ y _drafts/")
    args = ap.parse_args()
    dry = args.solo_listar

    if args.solo_imagenes:
        localize_existing(dry)
        localize_logo(dry)
        print("\n[✓] Imagenes listas. Revisa con:  bundle exec jekyll serve")
        return

    existing = existing_sources()
    skip = () if args.sobrescribir else set(existing)

    print("[*] Leyendo posts...")
    posts = from_xml(args.xml, args.blog) if args.xml else from_blog(args.blog, skip=skip)
    if not posts:
        sys.exit("[!] No se encontraron posts.")
    print(f"[*] {len(posts)} posts encontrados\n")

    labels, written = set(), 0
    for post in posts:
        print(f"[+] {post['title']}")
        labels.update(post["labels"])
        if post["url"] in existing and not args.sobrescribir:
            print(f"    = ya existe ({os.path.basename(existing[post['url']])}), se conserva")
            continue
        if not args.sin_imagenes:
            localize_images(post, dry=dry)
        if write_post(post, args.sobrescribir, existing, dry, args.blog):
            written += 1

    print("\n[*] Secciones y logo")
    ensure_label_pages(labels | LINKED_LABELS, dry)
    if not args.sin_imagenes:
        localize_logo(dry)

    print(f"\n[✓] Listo: {written} posts {'(simulado)' if dry else 'escritos en _posts/'}.")
    print("    Revisa con:  bundle exec jekyll serve   y abre http://127.0.0.1:4000")


if __name__ == "__main__":
    main()
