from odoo import models, fields

class CasaSte(models.Model):
    _name = 'casa.ste'
    _description = 'Société Casa'

    name = fields.Char(string='Nom', required=True)
    logo = fields.Binary(string="Logo")
    address = fields.Text(string='Adresse')
    core_ste_id = fields.Many2one('core.ste', string='Société (Source)')
