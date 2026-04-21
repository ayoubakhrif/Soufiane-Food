from odoo import models, fields

class SuiviChauffeur(models.Model):
    _name = 'suivi.chauffeur'
    _description = 'Chauffeur Suivi Transport'

    name = fields.Char(string='Nom', required=True)
    employee_id = fields.Many2one(
        'core.employee', 
        string='Employé', 
        domain="[('job_position_id.name', 'ilike', 'Chauffeur')]",
        help="Linked HR Employee. Filtered by job position 'Chauffeur'."
    )
