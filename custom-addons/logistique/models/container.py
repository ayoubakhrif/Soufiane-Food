from odoo import models, fields

class LogistiqueContainer(models.Model):
    _name = 'logistique.container'
    _description = 'Conteneur'

    _sql_constraints = [
        ('unique_container_per_entry', 'unique(entry_id, name)', 'Container number must be unique per entry!')
    ]

    name = fields.Char(string='Numéro Conteneur', required=True)
    entry_id = fields.Many2one('logistique.entry', string='Entry')
    dossier_id = fields.Many2one(
        'logistique.dossier',
        string='Dossier / BL',
        related='entry_id.dossier_id',
        store=True,
        readonly=True
    )
