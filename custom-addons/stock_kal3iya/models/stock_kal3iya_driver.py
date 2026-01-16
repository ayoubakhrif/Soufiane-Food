from odoo import models, fields

class StockKal3iyaDriver(models.Model):
    _name = 'stock.kal3iya.driver'
    _description = 'Chauffeurs Stock Kal3iya'

    name = fields.Char(string='Nom', required=True)
    employee_id = fields.Many2one(
        'core.employee', 
        string='Employé', 
        domain="[('job_position_id.name', 'ilike', 'Chauffeur')]",
        help="Linked HR Employee. Filtered by job position 'Chauffeur'."
    )