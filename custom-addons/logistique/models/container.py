from odoo import models, fields

class LogistiqueContainer(models.Model):
    _name = 'logistique.container'
    _description = 'Conteneur'

    _sql_constraints = [
        ('unique_container_per_dossier', 'unique(dossier_id, name)', 'Container number must be unique per dossier!')
    ]

    name = fields.Char(string='Numéro Conteneur', required=True)
    dossier_id = fields.Many2one('logistique.dossier', string='Dossier / BL')
