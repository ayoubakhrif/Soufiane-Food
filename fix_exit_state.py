import sys
import re

with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_exit.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r"\('draft',\s*'Brouillon'\),"
replacement = "('draft', 'Brouillon'),\n        ('registered', 'Enregistré'),"

content = re.sub(pattern, replacement, content)

with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_exit.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated exit state")
