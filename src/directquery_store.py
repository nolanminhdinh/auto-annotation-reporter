"""Publish canonical CSV snapshots to a dedicated local PostgreSQL DirectQuery store."""
from __future__ import annotations
import csv
import json
import math
import re
from datetime import date, datetime
from pathlib import Path

from src.reporting_pipeline import ROOT,TABLES,KEYS,SCHEMA_VERSION,_file_digest


def load_bundle(folder=None):
    folder=Path(folder or ROOT/'data/processed')
    pointer=json.loads((folder/'current.json').read_text(encoding='utf-8-sig'))
    sid=pointer['snapshot_id']
    if not re.fullmatch(r'S[a-f0-9]{24}',sid): raise ValueError('Invalid snapshot identity')
    bundle=(folder/pointer['relative_folder']).resolve()
    bundle.relative_to((folder/'snapshots').resolve())
    manifest=json.loads((bundle/'bundle.json').read_text(encoding='utf-8'))
    if manifest['snapshot_id']!=sid: raise ValueError('Bundle identity mismatch')
    tables={}
    for name,columns in TABLES.items():
        path=bundle/(name+'.csv')
        if _file_digest(path)!=manifest['sha256'][path.name]: raise ValueError('CSV checksum mismatch: '+name)
        with path.open(encoding='utf-8-sig',newline='') as stream:
            reader=csv.DictReader(stream)
            if reader.fieldnames!=list(columns): raise ValueError('CSV contract mismatch: '+name)
            rows=[]
            for raw in reader:
                row=[]
                for column,kind in columns.items():
                    value=raw[column]
                    if value=='': value=None
                    elif column in ('date_key','joined_date','as_of'): value=date.fromisoformat(value[:10])
                    elif kind=='INTEGER': value=int(value)
                    elif kind=='REAL':
                        value=float(value)
                        if not math.isfinite(value): raise ValueError('Non-finite CSV value')
                    row.append(value)
                rows.append(tuple(row))
            tables[name]=rows
    return sid,tables


def connect(config,reader=False):
    import pg8000.dbapi
    return pg8000.dbapi.connect(host='127.0.0.1',port=55432,database='annotation_reporting',
                               user='annotation_reader' if reader else 'annotation_owner',
                               password=config['reader_password' if reader else 'owner_password'],timeout=15)


def publish(config,folder=None):
    sid,tables=load_bundle(folder)
    conn=connect(config)
    try:
        cursor=conn.cursor()
        cursor.execute('SELECT pg_advisory_xact_lock(700173)')
        cursor.execute('CREATE TABLE IF NOT EXISTS publication_schema (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL)')
        cursor.execute('SELECT version FROM publication_schema WHERE id=1')
        version=cursor.fetchone()
        if version and version[0]!=SCHEMA_VERSION: raise ValueError('DirectQuery schema requires migration')
        cursor.execute('INSERT INTO publication_schema VALUES (1,%s) ON CONFLICT(id) DO NOTHING',(SCHEMA_VERSION,))
        cursor.execute('CREATE TABLE IF NOT EXISTS published_snapshots (snapshot_id TEXT PRIMARY KEY, published_at TIMESTAMPTZ NOT NULL DEFAULT now())')
        cursor.execute('CREATE TABLE IF NOT EXISTS serving_state (id INTEGER PRIMARY KEY CHECK(id=1),snapshot_id TEXT NOT NULL REFERENCES published_snapshots(snapshot_id))')
        cursor.execute('SELECT 1 FROM published_snapshots WHERE snapshot_id=%s',(sid,))
        exists=cursor.fetchone() is not None
        cursor.execute('INSERT INTO published_snapshots(snapshot_id) VALUES (%s) ON CONFLICT DO NOTHING',(sid,))
        for table,columns in TABLES.items():
            definitions=[]
            for column,kind in columns.items():
                datatype='DATE' if column in ('date_key','joined_date','as_of') else {'TEXT':'TEXT','INTEGER':'BIGINT','REAL':'DOUBLE PRECISION'}[kind]
                definitions.append(f'"{column}" {datatype}')
            cursor.execute(f'CREATE TABLE IF NOT EXISTS gold_{table} (snapshot_id TEXT NOT NULL REFERENCES published_snapshots(snapshot_id), '+', '.join(definitions)+f', PRIMARY KEY(snapshot_id,"{KEYS[table]}"))')
            fields=','.join('"'+column+'"' for column in columns)
            if not exists and tables[table]:
                cursor.executemany(f'INSERT INTO gold_{table} (snapshot_id,{fields}) VALUES ('+','.join(['%s']*(len(columns)+1))+')',[(sid,)+row for row in tables[table]])
            cursor.execute(f'CREATE OR REPLACE VIEW pbi_{table} AS SELECT '+','.join('g."'+column+'"' for column in columns)+f' FROM gold_{table} g JOIN serving_state s ON g.snapshot_id=s.snapshot_id AND s.id=1')
        cursor.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',('annotation_reader',))
        if not cursor.fetchone():
            cursor.execute("SELECT format('CREATE ROLE annotation_reader LOGIN PASSWORD %L',%s::text)",(config['reader_password'],))
            cursor.execute(cursor.fetchone()[0])
        cursor.execute('GRANT CONNECT ON DATABASE annotation_reporting TO annotation_reader')
        cursor.execute('GRANT USAGE ON SCHEMA public TO annotation_reader')
        cursor.execute('GRANT SELECT ON '+','.join('pbi_'+table for table in TABLES)+' TO annotation_reader')
        cursor.execute('INSERT INTO serving_state VALUES (1,%s) ON CONFLICT(id) DO UPDATE SET snapshot_id=EXCLUDED.snapshot_id',(sid,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally: conn.close()
    # Verify the same restricted login that Desktop will use, without exposing passwords.
    reader=connect(config,reader=True)
    try:
        cursor=reader.cursor()
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        cursor.execute('SELECT source_snapshot FROM pbi_report_status')
        if cursor.fetchone()[0]!=sid: raise ValueError('DirectQuery serving identity mismatch')
        for name,rows in tables.items():
            cursor.execute(f'SELECT count(*) FROM pbi_{name}')
            if cursor.fetchone()[0]!=len(rows): raise ValueError('DirectQuery row count mismatch: '+name)
        cursor.execute("SELECT has_table_privilege(current_user,'gold_dim_jobs','INSERT'),has_schema_privilege(current_user,'public','CREATE')")
        if any(cursor.fetchone()): raise ValueError('Desktop reader has unexpected write privileges')
    finally: reader.close()
    return {'snapshot_id':sid,'tables':{name:len(rows) for name,rows in tables.items()},'database':'annotation_reporting','endpoint':'127.0.0.1:55432','reader_verified':True,'row_counts_verified':True}
