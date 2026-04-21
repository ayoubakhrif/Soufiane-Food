from odoo import models, fields

class CasaDriver(models.Model):
    _name = 'casa_hanane.driver'
    _description = 'Chauffeurs Casa (Hanane)'

    name = fields.Char(string='Nom', required=True)
    phone = fields.Char(string='Téléphone')
    employee_id = fields.Many2one(
        'core.employee', 
        string='Employé',
        domain="[('job_position_id.name', 'ilike', 'Chauffeur')]"
    )
