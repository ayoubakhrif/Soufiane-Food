from odoo import models, fields, api
from datetime import date

class SuiviEmployee(models.Model):
    _name = 'suivi.employee'
    _description = 'Employé Suivi Présence'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    core_employee_id = fields.Many2one('core.employee', string='Employé Principal', required=True, tracking=True)
    
    # Related fields from Core Employee
    name = fields.Char(related='core_employee_id.name', store=True)
    phone = fields.Char(related='core_employee_id.phone', readonly=True)
    monthly_salary = fields.Float(related='core_employee_id.monthly_salary', string='Salaire mensuel', readonly=True, store=True)
    
    # Editable fields specific to this module
    payroll_site = fields.Selection([
        ('mediouna', 'Mediouna'),
        ('casa', 'Casa')
    ], string='Site de Paie', default='mediouna', required=True, tracking=True)
    
    # Relations
    presence_ids = fields.One2many('suivi.presence', 'employee_id', string='Présence')
    leave_ids = fields.One2many('suivi.leave', 'employee_id', string='Congés')
    
    # Leave Stats
    annual_leave_quota = fields.Integer(string='Quota Annuel', compute='_compute_leave_stats')
    leaves_taken = fields.Float(string='Congés Pris', compute='_compute_leave_stats')
    leaves_remaining = fields.Float(string='Solde Restant', compute='_compute_leave_stats')

    @api.depends('leave_ids.state', 'leave_ids.days_count', 'leave_ids.leave_type')
    def _compute_leave_stats(self):
        current_year = date.today().year
        config = self.env['suivi.presence.config'].get_main_config()
        quota = config.annual_leave_quota if config else 18
        
        for rec in self:
            rec.annual_leave_quota = quota
            taken = sum(l.days_count for l in rec.leave_ids 
                        if l.state == 'approved' 
                        and l.leave_type == 'paid'
                        and l.date_from.year == current_year)
            
            rec.leaves_taken = taken
            rec.leaves_remaining = quota - taken
