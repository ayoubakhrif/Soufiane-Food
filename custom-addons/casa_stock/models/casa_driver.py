from odoo import models, fields

class CasaDriver(models.Model):
    _name = 'casa.driver'
    _description = 'Chauffeurs Casa'

    name = fields.Char(string='Nom', required=True)
    phone = fields.Char(string='Téléphone')
    employee_id = fields.Many2one(
        'core.employee', 
        string='Employé',
        domain="[('job_position_id.name', 'ilike', 'Chauffeur')]"
    )
