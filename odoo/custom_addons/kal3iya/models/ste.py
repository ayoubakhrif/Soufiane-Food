from odoo import models, fields

class Kal3iyaste(models.Model):
    _name = 'kal3iya.ste'
    _description = 'Société'

    name = fields.Char(string='Sociétés', required=True)
    descrip = fields.Text(string='Informations')
    logo = fields.Binary(string="Logo", attachment=False)
    cachee = fields.Binary(string="Cachet", attachment=False)
    adress = fields.Text(string='Adresse', required=True)
    bl = fields.Char(string='BL')