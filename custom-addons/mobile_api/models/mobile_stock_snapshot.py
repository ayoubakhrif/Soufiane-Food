from odoo import models, fields, tools

class MobileStockSnapshot(models.Model):
    _name = 'mobile.stock.snapshot'
    _description = 'Mobile Stock Snapshot'
    _auto = False
    _order = 'entry_date, id'

    product_id = fields.Many2one('stock.kal3iya.product', string='Produit', readonly=True)
    product_name = fields.Char(string='Nom Produit', readonly=True)
    company_article_id = fields.Many2one('company.article', string='Article Société', readonly=True)
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
    ], string='Garage', readonly=True)
    lot = fields.Char(string='Lot', readonly=True)
    dum = fields.Char(string='DUM', readonly=True)
    quantity_available = fields.Float(string='Quantité Disponible', readonly=True)
    entry_date = fields.Datetime(string='Date Entrée (FIFO)', readonly=True)
    weight = fields.Float(string='Poids (Kg)', readonly=True)
    calibre = fields.Char(string='Calibre', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    min(m.id) as id,
                    m.product_id,
                    p.name as product_name,
                    p.company_article_id,
                    m.garage,
                    m.lot,
                    m.dum,
                    sum(m.qty) as quantity_available,
                    min(m.date) as entry_date,
                    max(m.weight) as weight,
                    max(m.calibre) as calibre
                FROM stock_kal3iya_move m
                JOIN stock_kal3iya_product p ON m.product_id = p.id
                WHERE m.state = 'done'
                GROUP BY m.product_id, p.name, p.company_article_id, m.garage, m.lot, m.dum
                HAVING sum(m.qty) > 0
            )
        """ % self._table)
