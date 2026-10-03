import sys
import re

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r"('weight': rec\.weight or 0\.0,\s*'quantity': rec\.quantity or 0\.0,)"
replacement = r"\1\n                'quantity_sellable': rec.quantity_sellable or 0.0,"

content = re.sub(pattern, replacement, content)

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated api_stock")
