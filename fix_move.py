import sys
import re

with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_move.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "        ('done', 'Fait'),\n    ], string='eâ€°tat', default='done', required=True)",
    "        ('done', 'Fait'),\n        ('registered', 'Enregistré'),\n    ], string='État', default='done', required=True)"
)

with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_move.py", "w", encoding="utf-8") as f:
    f.write(content)


with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "quantity = fields.Float(string='QuantitÃ©', readonly=True)",
    "quantity = fields.Float(string='Quantité (Physique)', readonly=True)\n    quantity_sellable = fields.Float(string='Quantité (Vendable)', readonly=True)"
)

sql_old = """                SELECT
                    min(m.id) as id,
                    m.product_id,
                    m.lot,
                    m.dum,
                    m.frigo,
                    m.weight,
                    m.calibre,
                    sum(m.qty) as quantity,
                    max(m.price_purchase) as price,
                    sum(m.qty * m.price_purchase) as mt_achat,
                    max(m.date) as write_date,
                    min(m.date) as create_date
                FROM
                    casa_field_stock_move m
                WHERE
                    m.state = 'done'"""
sql_new = """                SELECT
                    min(m.id) as id,
                    m.product_id,
                    m.lot,
                    m.dum,
                    m.frigo,
                    m.weight,
                    m.calibre,
                    sum(CASE WHEN m.state = 'done' THEN m.qty ELSE 0 END) as quantity,
                    sum(m.qty) as quantity_sellable,
                    max(m.price_purchase) as price,
                    sum(CASE WHEN m.state = 'done' THEN m.qty ELSE 0 END * m.price_purchase) as mt_achat,
                    max(m.date) as write_date,
                    min(m.date) as create_date
                FROM
                    casa_field_stock_move m
                WHERE
                    m.state IN ('done', 'registered')"""
content = content.replace(sql_old, sql_new)

with open("custom-addons/stock_casa_field/models/casa_field_stock_stock_stock.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated stock and move models")
