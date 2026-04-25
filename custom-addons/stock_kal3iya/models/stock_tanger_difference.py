from odoo import models, fields, tools

class StockTangerDifference(models.Model):
    _name = 'stock.tanger.difference'
    _description = 'Différence de stock Tanger'
    _auto = False
    _log_access = False
    _order = 'diff_kal_casa DESC'

    article_id = fields.Many2one('company.article', string='Article', readonly=True)
    qty_kal3iya = fields.Float(string='Quantité (Kal3iya)', readonly=True)
    qty_casa_tanger = fields.Float(string='Quantité (Casa Tanger)', readonly=True)
    qty_hanane_tanger = fields.Float(string='Quantité (Hanane Tanger)', readonly=True)
    diff_kal_casa = fields.Float(string='Diff (Kal3iya - Casa)', readonly=True)
    diff_kal_hanane = fields.Float(string='Diff (Kal3iya - Hanane)', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    a.id as id,
                    a.id as article_id,
                    COALESCE(k.qty, 0) as qty_kal3iya,
                    COALESCE(c.qty, 0) as qty_casa_tanger,
                    COALESCE(h.qty, 0) as qty_hanane_tanger,
                    (COALESCE(k.qty, 0) - COALESCE(c.qty, 0)) as diff_kal_casa,
                    (COALESCE(k.qty, 0) - COALESCE(h.qty, 0)) as diff_kal_hanane
                FROM company_article a
                LEFT JOIN (
                    SELECT p.company_article_id as article_id, SUM(m.qty) as qty
                    FROM stock_kal3iya_move m
                    JOIN stock_kal3iya_product p ON m.product_id = p.id
                    WHERE m.state = 'done'
                    GROUP BY p.company_article_id
                ) k ON k.article_id = a.id
                LEFT JOIN (
                    SELECT p.article_id, SUM(m.qty) as qty
                    FROM casa_stock_move m
                    JOIN casa_product p ON m.product_id = p.id
                    WHERE m.state = 'done' AND m.ville = 'tanger'
                    GROUP BY p.article_id
                ) c ON c.article_id = a.id
                LEFT JOIN (
                    SELECT p.article_id, SUM(m.qty) as qty
                    FROM casa_hanane_stock_move m
                    JOIN casa_hanane_product p ON m.product_id = p.id
                    WHERE m.state = 'done' AND m.ville = 'tanger'
                    GROUP BY p.article_id
                ) h ON h.article_id = a.id
                WHERE (COALESCE(k.qty, 0) != 0 OR COALESCE(c.qty, 0) != 0 OR COALESCE(h.qty, 0) != 0)
            )
        """)
