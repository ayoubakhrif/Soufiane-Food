from odoo import models, fields, api

class Kal3iyaClient(models.Model):
    _name = 'kal3iya.client'
    _description = 'Clients'

    name = fields.Char(string='Client', required=True)

    # Lignes de sorties automatiquement calculées
    sortie_ids = fields.One2many(
        'kal3iyasortie',
        'client_id',
        string='Sorties de ce client',
        compute='_compute_sortie_ids',
        store=False,
    )

    sortie_count = fields.Integer(
        string="Nombre de commandes",
        compute='_compute_sortie_ids'
    )

    avances = fields.One2many('kal3iya.advance', 'client_id', string='Avances')
    compte = fields.Float(readonly=True, compute='_compute_compte', store=True)

    def _compute_sortie_ids(self):
        """Récupère automatiquement les sorties liées à ce client"""
        for client in self:
            sorties = self.env['kal3iyasortie'].search([('client_id', '=', client.id)])
            client.sortie_ids = sorties
            client.sortie_count = len(sorties)


    # Lignes de retours automatiquement calculées
    retour_ids = fields.One2many(
        'kal3iyaentry',
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
            retours = self.env['kal3iyaentry'].search([('client_id', '=', client.id)])
            client.retour_ids = retours
            client.retour_count = len(retours)


    @api.depends('sortie_ids.mt_vente', 'avances.amount', 'retour_ids.selling_price', 'retour_ids.tonnage', 'retour_ids.state')
    def _compute_compte(self):
        """Compte = ventes - avances - retours"""
        for client in self:
            # 💰 Total des ventes
            total_ventes = sum(client.sortie_ids.mapped('mt_vente'))

            # 💵 Total des avances
            total_avances = sum(client.avances.mapped('amount'))

            # 🔄 Total des retours (entrées avec state='retour')
            retours = client.retour_ids.filtered(lambda r: r.state == 'retour')
            total_retours = sum(r.selling_price*r.tonnage for r in retours)

            # 🧮 Calcul final
            client.compte = total_ventes - total_avances - total_retours
