from odoo import models, fields, api

class CasaClient(models.Model):
    _name = 'casa.client'
    _description = 'Clients Casa'

    name = fields.Char(string='Nom', required=True)

    # Champ computed pour le nombre de commandes
    exit_count = fields.Integer(
        string='Commandes',
        compute='_compute_exit_count',
        store=True,
    )

    exit_ids = fields.One2many(
        'casa.stock.exit',
        'client_id',
        string='Sorties de ce client',
    )

    @api.depends('exit_ids', 'exit_ids.state')
    def _compute_exit_count(self):
        """Compte uniquement les sorties confirmées (done)"""
        for rec in self:
            rec.exit_count = len(rec.exit_ids.filtered(lambda s: s.state == 'done'))