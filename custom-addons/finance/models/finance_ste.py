from odoo import models, fields

class FinanceSte(models.Model):
    _name = 'finance.ste'
    _description = 'Société'

    name = fields.Char(string='Sociétés', required=True)
    descrip = fields.Text(string='Informations')
    logo = fields.Binary(string="Logo", attachment=False)
    cachee = fields.Binary(string="Cachet", attachment=False)
    adress = fields.Text(string='Adresse')
    num_compte = fields.Char(string='Numéro de compte')
    raison_social = fields.Char(string='Raison sociale')
    
    core_ste_id = fields.Many2one('core.ste', string='Société (Source)')
    is_zone_franche = fields.Boolean(related='core_ste_id.is_zone_franche', string='Zone Franche', readonly=True, store=True)