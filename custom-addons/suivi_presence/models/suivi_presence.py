from odoo import models, fields, api

class SuiviPresence(models.Model):
    _name = 'suivi.presence'
    _description = 'Suivi de Présence'
    _order = 'datetime desc'

    employee_id = fields.Many2one('suivi.employee', string='Employé', required=True, ondelete='cascade')
    
    # Related fields
    employee_phone = fields.Char(related='employee_id.phone', string='Téléphone', readonly=True)
    employee_site = fields.Selection(related='employee_id.payroll_site', string='Site de Paie', readonly=True)

    datetime = fields.Datetime(string='Date et Heure', required=True, default=fields.Datetime.now)
    type = fields.Selection([
        ('entree', 'Entrée'),
        ('sortie', 'Sortie')
    ], string='Type', required=True)
