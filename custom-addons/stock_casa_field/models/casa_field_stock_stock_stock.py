import odoo
﻿from odoo import models, fields, api, tools

class CasaStockStock(models.Model):
    ste_id = fields.Integer(string='Ancienne Societe (A ignorer)')
    _name = 'casa_field.stock.stock'
    _description = 'Stock Casa (Aggregation)'
    _auto = False
    _log_access = False
    _order = 'product_id'

    product_id = fields.Many2one('casa_field.stock.product', string='Produit', readonly=True)
    lot = fields.Char(string='Lot', readonly=True)
    dum = fields.Char(string='DUM', readonly=True)
    garage = fields.Selection([
        ('garage1', 'Garage 1'),
        ('garage2', 'Garage 2'),
        ('garage3', 'Garage 3'),
        ('garage4', 'Garage 4'),
        ('garage5', 'Garage 5'),
        ('garage6', 'Garage 6'),
        ('garage7', 'Garage 7'),
        ('garage8', 'Garage 8'),
        ('terrasse', 'Terrasse'),
        ('fenidek', 'Fenidek'),
    ], string='Garage', required=True)
    frigo = fields.Selection([
        ('frigo1', 'Frigo 1'),
        ('frigo2', 'Frigo 2'),
        ('stock_casa', 'Stock Casa'),
    ], string='Frigo', readonly=True)
    
    quantity = fields.Float(string='Quantité', readonly=True)
    weight = fields.Float(string='Poids (Kg)', readonly=True)
    calibre = fields.Char(string='Calibre', readonly=True)
    price = fields.Float(string='Dernier Prix (Achat)', readonly=True)
    mt_achat = fields.Float(string='Montant achat estimé', readonly=True)
    image_1920 = fields.Image(related='product_id.company_article_image', readonly=True)
    write_date = fields.Datetime(string='Last Update', readonly=True)
    create_date = fields.Datetime(string='Creation Date', readonly=True)

    def init(self):
        import odoo
        if not odoo.tools.table_exists(self.env.cr, "casa_field_stock_move"):
            self.env["casa_field.stock.move"]._auto_init()
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    min(m.id) as id,
                    0 as ste_id,
                    m.product_id,
                    m.lot,
                    m.dum,
                    m.garage,
                    m.frigo,
                    
                    sum(m.qty) as quantity,
                    max(m.weight) as weight,
                    max(m.calibre) as calibre,
                    max(m.price_purchase) as price,
                    sum(m.qty * m.price_purchase) as mt_achat,
                    max(m.date) as write_date,
                    min(m.date) as create_date
                FROM
                    casa_field_stock_move m
                WHERE
                    m.state = 'done'
                GROUP BY
                    m.product_id, m.lot, m.dum, m.garage, m.frigo
                HAVING
                    sum(m.qty) != 0
            )
        """ % self._table)

    def action_new_exit(self):
        self.ensure_one()
        return {
            'name': 'Nouvelle Sortie',
            'type': 'ir.actions.act_window',
            'res_model': 'casa_field.stock.exit',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_product_id': self.product_id.id,
                'default_lot': self.lot,
                'default_dum': self.dum,
                'default_garage': self.garage,
                'default_frigo': self.frigo,
                'default_weight': self.weight,
                'default_calibre': self.calibre,
                }
        }



