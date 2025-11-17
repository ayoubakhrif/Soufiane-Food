from odoo import models, fields

class FinanceSte(models.Model):
    _name = 'finance.ste'
    _description = 'Société'

    name = fields.Char(string='Sociétés', required=True)
    descrip = fields.Text(string='Informations')
    logo = fields.Binary(string="Logo", attachment=False)
    cachee = fields.Binary(string="Cachet", attachment=False)
    adress = fields.Text(string='Adresse')