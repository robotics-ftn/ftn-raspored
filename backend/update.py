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

with open('storage/source.txt', 'r') as izvor:

    for i in izvor:
        if i[0] == '#':
            continue
        naziv = i.replace('\n','').split('/')[-1]
        urllib.request.urlretrieve(i, f'storage/{naziv}.pdf')
        sql_db.execute(f"INSERT OR REPLACE INTO izvorni_dokument (id, url, naziv, dopremljeno, obradjeno, checksum) \
        VALUES ((SELECT id FROM izvorni_dokument WHERE url = '{i}'), '{i}', '{naziv}', {int(time.time())}, \
        (SELECT obradjeno FROM izvorni_dokument WHERE url = '{i}'), (SELECT checksum FROM izvorni_dokument WHERE url = '{i}'))")
        

sql_connector.commit()
sql_connector.close()
