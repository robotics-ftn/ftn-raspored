#! /usr/bin/env python3

import urllib.request
import sqlite3
import time
import html
import subprocess

cmd = """curl -s "https://ftn.uns.ac.rs/raspored-i-realizacija-2/" | awk '/Raspored nastave/,/<\/details>/' | grep -oP 'href="\\K[^"]*">[^<]+' | sed 's/">/ -> /'"""
output = subprocess.check_output(cmd, 
                                shell=True, 
                                text=True,
                                stderr=subprocess.DEVNULL)

names_links = []
for line in output.strip().split("\n"):
    if " -> " in line:
        link, name = line.split(" -> ")
        names_links.append((html.unescape(name), link))

with open("storage/source.txt", "w", encoding="utf-8") as f:
    for link in names_links:
        f.write(link[1] + "\n")

for line in names_links:
    print(f"{line[0]} -> {line[1]}")

sql_connector = sqlite3.connect('database/raspored.db')
sql_db = sql_connector.cursor()

with open('database/scripts/create.sql') as db_init:
    sql_db.executescript(db_init.read())

for name, link in names_links:
    if link[0] == '#':
        continue
    pdf_name = link.split('/')[-1].replace('.pdf','').lower()
    urllib.request.urlretrieve(link, f'storage/{pdf_name}.pdf')
    sql_db.execute(
        """
        INSERT INTO izvorni_dokument (url, naziv, pdf_naziv, dopremljeno, obradjeno, checksum)
        VALUES (?, ?, ?, ?, 0, NULL)
        ON CONFLICT(naziv) DO UPDATE SET
            url = excluded.url,
            pdf_naziv = excluded.pdf_naziv,
            dopremljeno = excluded.dopremljeno;
        """,
        (link, name, pdf_name, int(time.time()))
    )

sql_connector.commit()
sql_connector.close()
