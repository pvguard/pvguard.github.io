---
title: "Machine NOMBRE | Hack The Box | Medium"
tags: [hackthebox]
description: "Writeup de la máquina NOMBRE de Hack The Box: enumeración, explotación y escalada de privilegios."
image: /assets/img/posts/nombre/portada.png
---

<h1 style="text-align: center;"><span style="color: red;">Machine NOMBRE | Hack The Box</span></h1>

![Portada](/assets/img/posts/nombre/portada.png)

<!--more-->

## Enumeración

```bash
nmap -p- --open -sS --min-rate 5000 -n -Pn 10.10.11.XX -oG allPorts
nmap -sCV -p22,80 10.10.11.XX -oN targeted
```

## Explotación

Explica aquí el vector de entrada.

## Escalada de privilegios

```bash
sudo -l
```

> Copia este archivo a `_posts/AAAA-MM-DD-nombre-maquina.md` cuando lo publiques.
> Todo lo que esté antes de `<!--more-->` aparece en la portada (como en Blogger).
