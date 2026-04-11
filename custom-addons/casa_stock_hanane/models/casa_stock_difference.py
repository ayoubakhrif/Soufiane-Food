from odoo import models, fields, tools

class CasaStockDifference(models.Model):
    _name = 'casa_hanane.stock.difference'
    _description = 'Différence de stock'
    _auto = False
    _log_access = False

    article_id = fields.Many2one('company.article', string='Article (Company)', readonly=True)
    quantity_casa = fields.Float(string='Quantité (Casa)', readonly=True)
    quantity_hanane = fields.Float(string='Quantité (Hanane)', readonly=True)
    difference = fields.Float(string='Différence', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    a.id as id,
                    a.id as article_id,
                    COALESCE(casa_stock.quantity, 0) as quantity_casa,
                    COALESCE(hanane_stock.quantity, 0) as quantity_hanane,
                    (COALESCE(casa_stock.quantity, 0) - COALESCE(hanane_stock.quantity, 0)) as difference
                FROM company_article a
                LEFT JOIN (
                    SELECT p.article_id, sum(m.qty) as quantity
                    FROM casa_stock_move m
                    JOIN casa_product p ON m.product_id = p.id
                    WHERE m.state = 'done'
                    GROUP BY p.article_id
                ) casa_stock ON casa_stock.article_id = a.id
                LEFT JOIN (
                    SELECT p.article_id, sum(m.qty) as quantity
                    FROM casa_hanane_stock_move m
                    JOIN casa_hanane_product p ON m.product_id = p.id
                    WHERE m.state = 'done'
                    GROUP BY p.article_id
                ) hanane_stock ON hanane_stock.article_id = a.id
                WHERE (COALESCE(casa_stock.quantity, 0) - COALESCE(hanane_stock.quantity, 0)) != 0
            )
        """ % self._table)
