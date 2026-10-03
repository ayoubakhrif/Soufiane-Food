import sys

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "exit_rec = request.env['casa_field.stock.exit'].sudo().create(vals)\n                exit_rec.action_confirm()",
    "exit_rec = request.env['casa_field.stock.exit'].sudo().create(vals)\n                exit_rec.action_register()"
)

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated bulk exit")
