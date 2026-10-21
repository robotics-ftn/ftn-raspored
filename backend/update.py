#! /usr/bin/env python3

import urllib.request
import sqlite3
import time
import html
import subprocess
import hashlib

def checksum(filename):

    hasher = hashlib.sha256()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return int(hasher.hexdigest()[:15], base=16)

try:
    with open('storage/excluded.txt', 'r', encoding='utf-8') as f:
        excluded_names = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    excluded_names = []

cmd = """curl -s "https://ftn.uns.ac.rs/raspored-i-realizacija-2/" | awk '/Raspored nastave/,/<\/details>/' | grep -oP 'href="\\K[^"]*">[^<]+' | sed 's/">/ -> /'"""
output = subprocess.check_output(cmd, 
                                shell=True, 
                                text=True,
                                stderr=subprocess.DEVNULL)

files = []
for line in output.strip().split("\n"):
    if " -> " in line:
        link, name = line.split(" -> ")
        name = html.unescape(name)
        pdf_name = None
        csum = None
        if name not in excluded_names:
            print(f"{name} -> {link}") 
            pdf_name = link.split('/')[-1].replace('.pdf','').lower()
            file_path = f'storage/{pdf_name}.pdf'
            urllib.request.urlretrieve(link, file_path)
            csum = checksum(file_path)
        files.append((name, link, pdf_name, csum))

with open("storage/source.txt", "w", encoding="utf-8") as f:
    for link in files:
        f.write(link[1] + "\n")    

sql_connector = sqlite3.connect('database/raspored.db')
sql_db = sql_connector.cursor()

with open('database/scripts/create.sql') as db_init:
    sql_db.executescript(db_init.read())

for name, link, pdf_name, csum in files:
    if link[0] == '#':
        continue
    skip = False
    if name in excluded_names:
        skip = True
    sql_db.execute(
        """
        INSERT INTO izvorni_dokument (url, naziv, pdf_naziv, dopremljeno, preskoci, checksum)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(naziv) DO UPDATE SET
            dopremljeno = excluded.dopremljeno,
            preskoci = excluded.preskoci,
            checksum = excluded.checksum,
            url = CASE
                WHEN izvorni_dokument.checksum != excluded.checksum THEN excluded.url 
                ELSE izvorni_dokument.url 
            END,
            pdf_naziv = CASE
                WHEN izvorni_dokument.checksum != excluded.checksum THEN excluded.pdf_naziv 
                ELSE izvorni_dokument.pdf_naziv 
            END,
            obradjeno = CASE 
                WHEN izvorni_dokument.checksum != excluded.checksum THEN 0 
                ELSE izvorni_dokument.obradjeno 
            END;
        """,
        (link, name, pdf_name, int(time.time()), skip, csum)
    )

sql_connector.commit()
sql_connector.close()
