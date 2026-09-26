import codecs

with codecs.open('custom-addons/stock_casa_field/models/kal3iya_stock_driver.py', 'w', encoding='utf-8') as f:
    f.write('''from odoo import models, fields

class Kal3iyaStockDriverCasa(models.Model):
    _inherit = 'kal3iya.stock.driver'

''')
