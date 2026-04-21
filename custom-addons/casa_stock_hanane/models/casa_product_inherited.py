from odoo import models, fields, api
from odoo.exceptions import UserError

class CasaProductStandard(models.Model):
    _inherit = 'casa.product'

    def action_generate_product_report(self):
        self.ensure_one()
        # Find the Hanane product variant for this article
        hanane_product = self.env['casa_hanane.product'].search([('article_id', '=', self.article_id.id)], limit=1)
        
        if not hanane_product:
             raise UserError("Ce produit n'est pas configuré dans le module Hanane.")
             
        stock_records = self.env['casa_hanane.stock.stock'].search([
            ('product_id', '=', hanane_product.id),
            ('quantity', '>', 0)
        ])
        
        if not stock_records:
            raise UserError(f"Aucun stock disponible pour '{self.name}' dans le module Hanane.")
            
        return self.env.ref('casa_stock_hanane.action_report_casa_stock_product').report_action(stock_records)
