from odoo import models, fields, tools


class TresorerieAnalyseReport(models.Model):
    _name = 'tresorerie.analyse.report'
    _description = 'Analyse des Flux de Trésorerie'
    _auto = False
    _order = 'date desc'

    # -------------------------------------------------------------------------
    # Dimension fields
    # -------------------------------------------------------------------------
    date = fields.Date(string='Date', readonly=True)

    client_id = fields.Many2one(
        'tresorerie.client',
        string='Client',
        readonly=True,
    )
    payment_type = fields.Selection(
        [('especes', 'Espèces'), ('cheque', 'Chèque')],
        string='Mode de paiement',
        readonly=True,
    )
    move_type = fields.Selection(
        [('in', 'Entrée'), ('out', 'Sortie')],
        string='Sens du mouvement',
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Measure fields
    # -------------------------------------------------------------------------
    amount_in = fields.Float(
        string='Montant Entrant (MAD)',
        readonly=True,
        digits=(10, 2),
        group_operator='sum',
    )
    amount_out = fields.Float(
        string='Montant Sortant (MAD)',
        readonly=True,
        digits=(10, 2),
        group_operator='sum',
    )
    net_balance = fields.Float(
        string='Solde Net (MAD)',
        readonly=True,
        digits=(10, 2),
        group_operator='sum',
    )

    # -------------------------------------------------------------------------
    # SQL View init
    # -------------------------------------------------------------------------
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (

                -- ============================================================
                -- ENTRÉES  (tresorerie.paiement)
                -- All incoming payments, regardless of confirmation state.
                -- ============================================================
                SELECT
                    p.id                        AS id,
                    p.date                      AS date,
                    p.client_id                 AS client_id,
                    p.payment_type              AS payment_type,
                    'in'::varchar               AS move_type,
                    p.amount                    AS amount_in,
                    0.0                         AS amount_out,
                    p.amount                    AS net_balance

                FROM tresorerie_paiement p

                UNION ALL

                -- ============================================================
                -- SORTIES  (tresorerie.sortie — confirmed only)
                -- Only confirmed outflows count as real cash movements.
                -- ============================================================
                SELECT
                    -- Offset IDs to avoid collisions with paiement IDs.
                    (s.id + 1000000)            AS id,
                    s.date                      AS date,
                    s.client_id                 AS client_id,
                    s.payment_type              AS payment_type,
                    'out'::varchar              AS move_type,
                    0.0                         AS amount_in,
                    s.amount                    AS amount_out,
                    -s.amount                   AS net_balance

                FROM tresorerie_sortie s
                WHERE s.state = 'confirmed'

            )
        """ % self._table)
