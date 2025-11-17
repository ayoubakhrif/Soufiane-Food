from odoo import models, fields, api

class Cal3iyaClient(models.Model):
    _name = 'finance.benif'
    _description = 'Bénificiaires'

    name = fields.Char(string='Bénificiaire', required=True)

    # Lignes de sorties automatiquement calculées
    sortie_ids = fields.One2many(
        'data.cheque',
        'finance_benif_id',
        string='Chèques de ce bénificiaire',
        compute='_compute_sortie_ids',
        store=False,
    )

    sortie_count = fields.Integer(
        string="Nombre de commandes",
        compute='_compute_sortie_ids'
    )

    def _compute_sortie_ids(self):
        """Récupère automatiquement les sorties liées à ce client"""
        for client in self:
            sorties = self.env['cal3iyasortie'].search([('client_id', '=', client.id)])
            client.sortie_ids = sorties
            client.sortie_count = len(sorties)


    # Lignes de retours automatiquement calculées
    retour_ids = fields.One2many(
        'cal3iyaentry',
        'client_id',
        string='Retours de ce client',
        compute='_compute_retour_ids',
        store=False,
    )

    retour_count = fields.Integer(
        string="Nombre de retours",
        compute='_compute_retour_ids'
    )


    def _compute_retour_ids(self):
        """Récupère automatiquement les retours liées à ce client"""
        for client in self:
            retours = self.env['data.cheque'].search([('client_id', '=', client.id)])
            client.retour_ids = retours
            client.retour_count = len(retours)
