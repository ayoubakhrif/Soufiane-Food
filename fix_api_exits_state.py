import sys

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "'qty': rec.qty,\n                    'returned_qty': returned_qty,",
    "'qty': rec.qty,\n                    'returned_qty': returned_qty,\n                    'state': rec.state,"
)

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Added state to api_exits")
