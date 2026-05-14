from odoo import models, fields, tools

class CasaStockDifference(models.Model):
    _name = 'casa_hanane.stock.difference'
    _description = 'Différence de stock'
    _auto = False
    _log_access = False
    _order = 'abs_difference DESC'

    article_id = fields.Many2one('company.article', string='Article (Company)', readonly=True)
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
    ], string='Ville', readonly=True)
    quantity_casa = fields.Float(string='Stock Provisoire (Casa)', readonly=True)
    quantity_hanane = fields.Float(string='Stock Provisoire (Hanane)', readonly=True)
    difference = fields.Float(string='Différence', readonly=True)
    abs_difference = fields.Float(string='Différence absolue', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    (hashtext(a.id::text || cities.ville) & 2147483647) as id,
                    a.id as article_id,
                    cities.ville as ville,
                    COALESCE(casa_stock.quantity, 0) as quantity_casa,
                    COALESCE(hanane_stock.quantity, 0) as quantity_hanane,
                    (COALESCE(casa_stock.quantity, 0) - COALESCE(hanane_stock.quantity, 0)) as difference,
                    ABS(COALESCE(casa_stock.quantity, 0) - COALESCE(hanane_stock.quantity, 0)) as abs_difference
                FROM company_article a
                CROSS JOIN (SELECT 'tanger' as ville UNION SELECT 'casa') cities
                LEFT JOIN (
                    SELECT p.article_id, m.ville, sum(m.qty) as quantity
                    FROM casa_stock_move m
                    JOIN casa_product p ON m.product_id = p.id
                    WHERE m.state = 'done'
                    GROUP BY p.article_id, m.ville
                ) casa_stock ON casa_stock.article_id = a.id AND casa_stock.ville = cities.ville
                LEFT JOIN (
                    SELECT p.article_id, m.ville, sum(m.qty) as quantity
                    FROM casa_hanane_stock_move m
                    JOIN casa_hanane_product p ON m.product_id = p.id
                    WHERE m.state = 'done'
                    GROUP BY p.article_id, m.ville
                ) hanane_stock ON hanane_stock.article_id = a.id AND hanane_stock.ville = cities.ville
                WHERE (casa_stock.quantity IS NOT NULL OR hanane_stock.quantity IS NOT NULL)
            )
        """ % self._table)
