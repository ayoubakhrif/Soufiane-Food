from odoo import models, fields, api
from datetime import date

class SuiviEmployee(models.Model):
    _name = 'suivi.employee'
    _description = 'Employé Suivi Présence'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'custom_employee_id'

    custom_employee_id = fields.Many2one('custom.employee', string='Employé Principal', required=True, tracking=True)
    
    # Related fields
    name = fields.Char(related='custom_employee_id.name', store=True)
    phone = fields.Char(related='custom_employee_id.phone', readonly=True)
    
    # Editable fields specific to this module (as requested)
    monthly_salary = fields.Float(string='Salaire mensuel', required=True, tracking=True)
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

    @api.onchange('custom_employee_id')
    def _on_change_custom_employee(self):
        if self.custom_employee_id:
            self.monthly_salary = self.custom_employee_id.monthly_salary
            self.payroll_site = self.custom_employee_id.payroll_site

    @api.depends('leave_ids.state', 'leave_ids.days_count', 'leave_ids.leave_type')
    def _compute_leave_stats(self):
        current_year = date.today().year
        config = self.env['suivi.config'].get_main_config()
        quota = config.annual_leave_quota if config else 18
        
        for rec in self:
            rec.annual_leave_quota = quota
            taken = sum(l.days_count for l in rec.leave_ids 
                        if l.state == 'approved' 
                        and l.leave_type == 'paid'
                        and l.date_from.year == current_year)
            
            rec.leaves_taken = taken
            rec.leaves_remaining = quota - taken
