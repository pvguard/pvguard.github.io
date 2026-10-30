# PVGuard Cybersecurity Technology — sitio Jekyll

Réplica del diseño de **pvguard.blogspot.com** (tema Matrix / terminal) lista para
publicar gratis en **GitHub Pages**. Escribes tus notas en Markdown o HTML, haces
`git push` y el sitio se actualiza solo.

```
_config.yml              ← título, descripción, redes sociales, logo
_data/menu.yml           ← menú principal y submenús (Labs, Workspace, Downloads…)
_posts/                  ← tus publicaciones (AAAA-MM-DD-slug.html o .md)
_drafts/                 ← borradores y la plantilla de writeup
assets/css/pvguard.css   ← colores y estilos (variables al inicio del archivo)
search/label/*.html      ← una página por etiqueta (/search/label/red-team/)
scripts/migrar_blogger.py← trae todos tus posts desde Blogger
_headers                 ← cabeceras de seguridad (solo Cloudflare Pages)
```

## 1. Publicarlo en GitHub Pages

1. En GitHub crea un repositorio **público** llamado `pvguard.github.io`.
2. Sube todo el contenido de esta carpeta:
   ```bash
   cd pvguard-site
   git init && git add . && git commit -m "PVGuard: sitio inicial"
   git branch -M main
   git remote add origin https://github.com/pvguard/pvguard.github.io.git
   git push -u origin main
   ```
3. En el repo: **Settings → Pages → Build and deployment → Source: Deploy from a branch**,
   rama `main`, carpeta `/ (root)`.
4. En uno o dos minutos el sitio queda en `https://pvguard.github.io`.

**¿Prefieres tenerlo en la carpeta `/docs` de otro repositorio?** Copia todo el contenido de
esta carpeta dentro de `docs/` en ese repo y en **Settings → Pages** elige la rama `main` y la
carpeta `/docs`. En ese caso el sitio queda en `https://pvguard.github.io/NOMBRE-DEL-REPO/`,
así que pon `baseurl: "/NOMBRE-DEL-REPO"` en `_config.yml`.

## 2. Tus posts (ya migrados) y las imágenes

Los 26 posts publicados ya están en `_posts/`, con su fecha y hora exactas, etiquetas,
el corte de "Leer más" y las mismas URLs que en Blogger (`/2026/07/ghostinject.html`).
El borrador **OSCP Review** está en `_drafts/` (no se publica hasta que lo muevas a `_posts/`).
Los enlaces internos que apuntaban a `pvguard.blogspot.com` ya apuntan al sitio nuevo.

Falta un paso, que tiene que correr en tu máquina: **bajar las imágenes** (siguen alojadas
en Blogger). Sin dependencias, solo Python 3:

```bash
python3 scripts/migrar_blogger.py --solo-imagenes --solo-listar   # ver qué va a bajar
python3 scripts/migrar_blogger.py --solo-imagenes                 # descargarlas
git add . && git commit -m "Imágenes locales" && git push
```

Las guarda en `assets/img/posts/` y reescribe las rutas en cada post. También baja el logo
de la cabecera. Si no lo corres, el sitio funciona igual, pero las imágenes seguirán
cargando desde Blogger.

Para volver a migrar desde una copia nueva de Blogger (feed.atom de Takeout o el .xml de
*Configuración → Hacer copia de seguridad del contenido*):

```bash
python3 scripts/migrar_blogger.py --xml feed.atom             # solo agrega posts nuevos
python3 scripts/migrar_blogger.py --xml feed.atom --sobrescribir
```

## 3. Ver el sitio en local (opcional)

```bash
sudo apt install ruby-full build-essential   # Kali / Debian
gem install bundler
bundle install
bundle exec jekyll serve
# abre http://127.0.0.1:4000
```

## 4. Escribir una nota nueva

1. Copia `_drafts/plantilla-writeup.md` a `_posts/2026-11-05-machine-nombre.md`.
2. Cambia `title`, `tags` e `image`. Las etiquetas deciden en qué sección del menú aparece:
   `hackthebox`, `tryhackme`, `otros`, `red team`, `blue team`, `Certificaciones`,
   `repositorios`, `libros`, `descargas`, `articulos`, `workspace`, `labs`.
3. Todo lo que pongas antes de `<!--more-->` sale en la portada con el botón
   **PULSE AQUI PARA LEER ESTE ARTICULO»**.
4. Las imágenes van en `assets/img/posts/<nombre>/`.
5. `git add . && git commit -m "Nuevo writeup" && git push`.

Si usas una etiqueta nueva, crea `search/label/<etiqueta>.html` copiando cualquiera de
los existentes (el script de migración lo hace solo).

## 5. Personalizar

- **Textos y redes:** `_config.yml` (`sidebar`, `social`).
- **Menú:** `_data/menu.yml`.
- **Estilo:** en `_config.yml`, `estilo: cyan` (panel hacker cian, el CSS cyan de tu
  plantilla de Blogger) o `estilo: green` (Matrix verde, como se ve hoy el blog).
- **Colores:** variables al inicio de `assets/css/pvguard-cyan.css` o `pvguard-green.css`
  (`--pv-cyan`, `--pv-text`, `--pv-white`…).

## 6. Dominio propio (ej. pvguard.com)

1. Crea un archivo `CNAME` en la raíz con una sola línea: `pvguard.com`.
2. En tu proveedor de dominio apunta los registros A a las IPs de GitHub Pages
   (185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153) y un
   `CNAME` de `www` a `pvguard.github.io`.
3. Cambia `url:` en `_config.yml` y activa **Enforce HTTPS** en Settings → Pages.

## 7. Cabeceras de seguridad

GitHub Pages no permite cabeceras propias. Si publicas el mismo repo en
**Cloudflare Pages** (gratis, *Framework preset: Jekyll*), se aplican las de `_headers`
(HSTS, CSP, X-Frame-Options, etc.). Buen caso para probar tu Security Headers Checker
y tu Checker Clickjacking contra tu propio sitio.

## Cambios respecto al Blogger original

- Estilo **hacker cyan** activado: el diseño cyan que ya estaba en tu plantilla pero que
  Blogger nunca mostraba (el bloque `<style>` empezaba con `<![CDATA[` y el navegador lo
  descartaba entero).
- Diseño **responsive**: menú hamburguesa y barra lateral debajo en móvil
  (Blogger estaba fijado a 1100 px).
- Submenús oscuros a juego con el tema (en Blogger salían en blanco).
- Buscador propio (`/buscar/`) y página de archivo (`/archivo/`).
- Se quitaron los widgets "Información del visitante" y "Vistas a la página".
