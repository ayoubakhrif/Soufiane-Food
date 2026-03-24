from odoo import models, fields, api, tools

class FinanceChequeEffetCalendar(models.Model):
    _name = 'finance.cheque.effet.calendar'
    _description = 'Calendrier global Chèques et Effets'
    _auto = False

    name = fields.Char(string='Référence', readonly=True)
    date_echeance = fields.Date(string="Date d'échéance", readonly=True)
    amount = fields.Float(string='Montant', readonly=True)
    benif_id = fields.Many2one('finance.benif', string='Bénéficiaire', readonly=True)
    ste_id = fields.Many2one('finance.ste', string='Société', readonly=True)
    type_doc = fields.Selection([
        ('cheque', 'Chèque'), 
        ('effet', 'Effet')
    ], string='Type', readonly=True)
    state = fields.Selection([
        ('encaisse', 'Encaissé'),
        ('non_encaisse', 'Non encaissé'),
        ('annule', 'Annulé'),
        ('bureau', 'Bureau'),
    ], string='État', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    (d.id * 10) + 1 AS id,
                    d.chq AS name,
                    d.date_echeance AS date_echeance,
                    d.amount AS amount,
                    d.benif_id AS benif_id,
                    d.ste_id AS ste_id,
                    'cheque' AS type_doc,
                    CASE 
                        WHEN d.state IN ('annule', 'bureau') THEN d.state
                        WHEN d.date_encaissement IS NOT NULL THEN 'encaisse'
                        ELSE 'non_encaisse'
                    END AS state
                FROM datacheque d
                WHERE d.active = True

                UNION ALL

                SELECT
                    (e.id * 10) + 2 AS id,
                    e.serie AS name,
                    e.date_echeance AS date_echeance,
                    e.montant AS amount,
                    e.benif_id AS benif_id,
                    e.ste_id AS ste_id,
                    'effet' AS type_doc,
                    CASE 
                        WHEN e.date_encaissement IS NOT NULL THEN 'encaisse'
                        ELSE 'non_encaisse'
                    END AS state
                FROM finance_effet e
            )
        """ % self._table)
