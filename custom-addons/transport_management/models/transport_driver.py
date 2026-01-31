from odoo import models, fields

class TransportDriver(models.Model):
    _name = 'transport.driver'
    _description = 'Chauffeurs Transport'

    name = fields.Char(string='Nom', required=True)
    employee_id = fields.Many2one(
        'core.employee', 
        string='Employé', 
        domain="[('job_position_id.name', 'ilike', 'Chauffeur')]",
        help="Linked HR Employee. Filtered by job position 'Chauffeur'."
    )
    
    monthly_summary_ids = fields.One2many('transport.driver.monthly.summary', 'driver_id', string='Suivi Salaire')
    advance_ids = fields.One2many('transport.driver.advance', 'driver_id', string='Avances')
