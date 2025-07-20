import sqlite3
import json
from pathlib import Path

DB_FILENAME = Path(__file__).parent / "kakeibo.db"

def dump_table_to_json(conn, table_name):
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        records = []
        for row in rows:
            records.append(dict(zip(columns, row)))
        return records
    except Exception as e:
        print(f"Error dumping table {table_name}: {e}")
        return None

conn = sqlite3.connect(DB_FILENAME)

data_to_seed = {}

tables = ["main_categories", "sub_categories", "transactions", "backup_time"]
for table in tables:
    table_data = dump_table_to_json(conn, table)
    if table_data is not None:
        data_to_seed[table] = table_data

conn.close()

output_file = Path(__file__).parent / "kakeibo_data.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data_to_seed, f, indent=4, ensure_ascii=False)

print(f"Data dumped to {output_file}")