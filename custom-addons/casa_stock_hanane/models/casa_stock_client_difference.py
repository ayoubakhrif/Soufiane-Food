from odoo import models, fields, tools

class CasaStockClientDifference(models.Model):
    _name = 'casa_hanane.client.difference'
    _description = 'Différence de soldes clients (Casa vs Hanane)'
    _auto = False
    _log_access = False

    client_name = fields.Char(string='Client', readonly=True)
    compte_total_casa = fields.Float(string='Solde Total (Casa)', readonly=True)
    compte_total_hanane = fields.Float(string='Solde Total (Hanane)', readonly=True)
    difference = fields.Float(string='Différence', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    (hashtext(COALESCE(c1.name, c2.name)) & 2147483647) AS id,
                    COALESCE(c1.name, c2.name) AS client_name,
                    COALESCE(c1.compte_total, 0) AS compte_total_casa,
                    COALESCE(c2.compte_total, 0) AS compte_total_hanane,
                    (COALESCE(c1.compte_total, 0) - COALESCE(c2.compte_total, 0)) AS difference
                FROM casa_client c1
                FULL OUTER JOIN casa_hanane_client c2 ON LOWER(TRIM(c1.name)) = LOWER(TRIM(c2.name))
                WHERE (COALESCE(c1.compte_total, 0) - COALESCE(c2.compte_total, 0)) != 0
            )
        """ % self._table)
