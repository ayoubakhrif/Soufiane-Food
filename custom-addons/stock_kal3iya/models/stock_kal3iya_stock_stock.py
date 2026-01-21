from odoo import models, fields, api, tools

class StockKal3iyaStock(models.Model):
    _name = 'stock.kal3iya.stock'
    _description = 'Stock Kal3iya (Aggregation)'
    _auto = False
    _log_access = False
    _order = 'product_id'

    product_id = fields.Many2one('stock.kal3iya.product', string='Produit', readonly=True, required=True)
    lot = fields.Char(string='Lot', readonly=True, required=True)
    dum = fields.Char(string='DUM', readonly=True, required=True)
    scan_dum = fields.Char(string='Scan DUM', readonly=True)
    scan_invoice = fields.Char(string='Scan Facture', readonly=True)
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
    ], string='Garage')
    ste_id = fields.Many2one('stock.kal3iya.ste', string='Société', readonly=True)
    
    quantity = fields.Float(string='Quantité', readonly=True)
    weight = fields.Float(string='Poids (Kg)', readonly=True)
    calibre = fields.Char(string='Calibre', readonly=True)
    price = fields.Float(string='Dernier Prix (Achat)', readonly=True)
    mt_achat = fields.Float(string='Montant achat estimé', readonly=True)
    image_1920 = fields.Image(related='product_id.company_article_image', readonly=True)
    write_date = fields.Datetime(string='Last Update', readonly=True)
    create_date = fields.Datetime(string='Creation Date', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW stock_kal3iya_stock AS (
                SELECT
                    min(m.id) as id,
                    m.product_id,
                    m.lot,
                    m.dum,
                    max(m.scan_dum) as scan_dum,
                    max(m.scan_invoice) as scan_invoice,
                    m.garage,
                    m.ste_id,
                    sum(m.qty) as quantity,

                    max(CASE WHEN m.qty > 0 THEN m.weight END) as weight,
                    max(CASE WHEN m.qty > 0 THEN m.calibre END) as calibre,
                    max(CASE WHEN m.qty > 0 THEN m.price_purchase END) as price,

                    sum(m.qty * m.price_purchase) as mt_achat,
                    max(m.date) as write_date,
                    min(m.date) as create_date
                FROM
                    stock_kal3iya_move m
                WHERE
                    m.state = 'done'
                GROUP BY
                    m.product_id, m.lot, m.dum, m.garage, m.ste_id
                HAVING
                    sum(m.qty) != 0
            )
        """)

    def action_new_exit(self):
        self.ensure_one()
        return {
            'name': 'Nouvelle Sortie',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.kal3iya.exit',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_product_id': self.product_id.id,
                'default_lot': self.lot,
                'default_dum': self.dum,
                'default_garage': self.garage,
                'default_weight': self.weight,
                'default_calibre': self.calibre,
                'default_ste_id': self.ste_id.id, 
            }
        }

    def action_open_dum(self):
        self.ensure_one()
        if self.scan_dum:
            return {
                'type': 'ir.actions.act_url',
                'url': self.scan_dum,
                'target': 'new',
            }
        return False

    def action_open_invoice(self):
        self.ensure_one()
        if self.scan_invoice:
            return {
                'type': 'ir.actions.act_url',
                'url': self.scan_invoice,
                'target': 'new',
            }
        return False