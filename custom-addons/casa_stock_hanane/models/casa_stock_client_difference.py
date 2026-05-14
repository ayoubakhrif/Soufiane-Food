from odoo import models, fields, tools

class CasaStockClientDifference(models.Model):
    _name = 'casa_hanane.client.difference'
    _description = 'Différence de soldes clients (Casa vs Hanane)'
    _auto = False
    _log_access = False
    _order = 'abs_difference DESC'

    client_name = fields.Char(string='Client', readonly=True)
    compte_total_casa = fields.Float(string='Solde Total (Casa)', readonly=True)
    compte_total_hanane = fields.Float(string='Solde Total (Hanane)', readonly=True)
    difference = fields.Float(string='Différence', readonly=True)
    abs_difference = fields.Float(string='Différence absolue', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    (hashtext(COALESCE(c1.name, c2.name)) & 2147483647) AS id,
                    COALESCE(c1.name, c2.name) AS client_name,
                    COALESCE(c1.compte_provisoire, 0) AS compte_total_casa,
                    COALESCE(c2.compte_provisoire, 0) AS compte_total_hanane,
                    (COALESCE(c1.compte_provisoire, 0) - COALESCE(c2.compte_provisoire, 0)) AS difference,
                    ABS(COALESCE(c1.compte_provisoire, 0) - COALESCE(c2.compte_provisoire, 0)) AS abs_difference
                FROM (
                    SELECT LOWER(TRIM(name)) as match_name, MAX(name) as name, SUM(compte_provisoire) as compte_provisoire
                    FROM casa_client
                    GROUP BY LOWER(TRIM(name))
                ) c1
                FULL OUTER JOIN (
                    SELECT LOWER(TRIM(name)) as match_name, MAX(name) as name, SUM(compte_provisoire) as compte_provisoire
                    FROM casa_hanane_client
                    GROUP BY LOWER(TRIM(name))
                ) c2 ON c1.match_name = c2.match_name
            )
        """ % self._table)
