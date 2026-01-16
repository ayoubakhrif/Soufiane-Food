from odoo import models, fields

class Kal3iyaStockDriver(models.Model):
    _name = 'kal3iya.stock.driver'
    _description = 'Chauffeurs Stock Kal3iya'

    name = fields.Char(string='Nom', required=True)
    employee_id = fields.Many2one(
        'core.employee', 
        string='Employé', 
        domain="[('job_position_id.name', 'ilike', 'Chauffeur')]",
        help="Linked HR Employee. Filtered by job position 'Chauffeur'."
    )
