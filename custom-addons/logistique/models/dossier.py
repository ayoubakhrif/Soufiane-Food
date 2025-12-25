from odoo import models, fields

class LogistiqueDossier(models.Model):
    _name = 'logistique.dossier'
    _description = 'Dossier Logistique'
    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Le numéro de BL doit être unique !"),
    ]

    name = fields.Char(string='Numéro BL', required=True)
    container_ids = fields.One2many('logistique.container', 'dossier_id', string='Conteneurs')
    cheque_ids = fields.One2many('logistique.dossier.cheque', 'dossier_id', string='Chèques')

