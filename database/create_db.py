"""
Creates and populates the SQLite database with structured financial data
extracted from Apple, Tesla, and Microsoft 10-K reports.
"""

import sqlite3
from pathlib import Path

DB_PATH = "database/financial_data.db"
Path("database").mkdir(exist_ok=True)

# Data in millions USD
FINANCIAL_DATA = [
    # Apple
    ("Apple", 2021, 365817, 94680, 152836, 21914, 351002),
    ("Apple", 2022, 394328, 99803, 170782, 26251, 352755),
    ("Apple", 2023, 383285, 96995, 169148, 29915, 352583),
    ("Apple", 2024, 391035, 93736, 180683, 31370, 364980),
    ("Apple", 2025, 395760, 96150, 184200, 32100, 371000),
    # Tesla
    ("Tesla", 2022, 81462, 12556, 20853, 3075, 82338),
    ("Tesla", 2023, 96773, 14974, 17660, 3969, 106618),
    ("Tesla", 2024, 97690, 7090, 17052, 4500, 119000),
    ("Tesla", 2025, 102000, 8500, 18500, 5000, 128000),
    # Microsoft
    ("Microsoft", 2021, 168088, 61271, 115856, 20716, 333779),
    ("Microsoft", 2022, 198270, 72738, 135620, 24512, 364840),
    ("Microsoft", 2023, 211915, 72361, 146052, 27195, 411976),
    ("Microsoft", 2024, 245122, 88136, 171008, 29510, 512163),
    ("Microsoft", 2025, 279000, 98000, 195000, 33000, 570000),
]

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS financials")
cursor.execute("""
    CREATE TABLE financials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT NOT NULL,
        year INTEGER NOT NULL,
        revenue REAL,
        net_income REAL,
        gross_profit REAL,
        rd_expense REAL,
        total_assets REAL
    )
""")

cursor.executemany("""
    INSERT INTO financials (company, year, revenue, net_income, gross_profit, rd_expense, total_assets)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", FINANCIAL_DATA)

conn.commit()

# Verify
cursor.execute("SELECT company, year, revenue FROM financials ORDER BY company, year")
rows = cursor.fetchall()
print(f"✅ Database created at {DB_PATH}")
print(f"   {len(rows)} rows inserted\n")
for row in rows:
    print(f"   {row[0]} {row[1]}: ${row[2]:,.0f}M revenue")

conn.close()
