"""Export the configured Django SQLite schema without application data."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

import django

django.setup()

from django.db import connection


def main():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT type, name, sql
            FROM sqlite_master
            WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
            ORDER BY CASE type
                WHEN 'table' THEN 0
                WHEN 'index' THEN 1
                WHEN 'view' THEN 2
                WHEN 'trigger' THEN 3
                ELSE 4
            END, name
        """)
        schema_objects = cursor.fetchall()

    lines = [
        '-- Current Sulong-NIR schema snapshot (SQLite).',
        '-- Schema only: no application data is included.',
        '-- Generated from the configured database after applying Django migrations.',
        '-- Django app migrations remain the authoritative schema history.',
        'PRAGMA foreign_keys = ON;',
        '',
    ]
    for _kind, _name, statement in schema_objects:
        lines.extend((statement.rstrip(';') + ';', ''))

    output = Path(__file__).with_name('current-schema.sql')
    output.write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    table_count = sum(kind == 'table' for kind, _, _ in schema_objects)
    print(f'Wrote {output} with {table_count} tables and {len(schema_objects)} schema objects.')


if __name__ == '__main__':
    main()
