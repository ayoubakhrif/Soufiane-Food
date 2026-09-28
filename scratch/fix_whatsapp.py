import os

file_path = r"c:\odoo-repos\Soufiane-Food\custom-addons\stock_casa_field\controllers\api_stock.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace product.product with casa_field.stock.product
content = content.replace(
    "product = request.env['product.product'].sudo().browse(int(line.get('product_id'))).name",
    "product = request.env['casa_field.stock.product'].sudo().browse(int(line.get('product_id'))).name"
)

# Replace order_ref with the joined exit references
content = content.replace(
    "msg += f\"Réf: {order_ref}\\n\"",
    """exits_records = request.env['casa_field.stock.exit'].sudo().browse(created_exits)
                refs = ", ".join(exits_records.mapped('name'))
                msg += f"Réf: {refs}\\n\""""
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed product_id and reference.")
