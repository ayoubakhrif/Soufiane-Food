from odoo import models, fields, api

class LogistiqueDossier(models.Model):
    _name = 'logistique.dossier'
    _description = 'Dossier Logistique'
    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Le numéro de BL doit être unique !"),
    ]

    name = fields.Char(string='Numéro BL', required=True)
    
    # Finance-managed fields
    prov_number = fields.Char(string='N° Prov', help="Numéro provisoire géré par Finance")
    def_number = fields.Char(string='N° Def', help="Numéro définitif géré par Finance")
    
    # One2many relationships
    container_ids = fields.One2many('logistique.container', 'dossier_id', string='Conteneurs')
    cheque_ids = fields.One2many('logistique.dossier.cheque', 'dossier_id', string='Chèques')
    entry_ids = fields.One2many('logistique.entry', 'dossier_id', string='Entrées Logistiques')

    container_count = fields.Integer(
        string="Nb Conteneurs",
        compute="_compute_counts",
        store=True
    )

    cheque_count = fields.Integer(
        string="Nb Chèques",
        compute="_compute_counts",
        store=True
    )

    @api.depends('container_ids', 'cheque_ids')
    def _compute_counts(self):
        for dossier in self:
            dossier.container_count = len(dossier.container_ids)
            dossier.cheque_count = len(dossier.cheque_ids)