from odoo import models, fields

class CasaStockDriver(models.Model):
    _name = 'casa.stock.driver'
    _description = 'Chauffeurs Stock Casa'

    name = fields.Char(string='Nom', required=True)
    employee_id = fields.Many2one(
        'core.employee', 
        string='EmployÃ©', 
        domain="[('job_position_id.name', 'ilike', 'Chauffeur')]",
        help="Linked HR Employee. Filtered by job position 'Chauffeur'."
    )
    phone = fields.Char(string='Telephone')
    password = fields.Char(string='Mot de passe')
