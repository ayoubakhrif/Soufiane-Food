import sys
import re

with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_move.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r"\('done',\s*'Fait'\),"
replacement = "('done', 'Fait'),\n        ('registered', 'Enregistré'),"

content = re.sub(pattern, replacement, content)

with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_move.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated stock move state")
