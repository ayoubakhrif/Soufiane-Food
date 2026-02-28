from odoo import models, fields, api

class CustomEmployee(models.Model):
    _name = 'custom.employee'
    _description = 'Custom Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom complet', required=True, tracking=True)
    phone = fields.Char(string='Numéro de téléphone', tracking=True)
    monthly_salary = fields.Float(string='Salaire mensuel', required=True, tracking=True)
    payroll_site = fields.Selection([
        ('mediouna', 'Mediouna'),
        ('casa', 'Casa')
    ], string='Site de Paie', default='mediouna', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    
    attendance_ids = fields.One2many('custom.attendance', 'employee_id', string='Présence')
    
    # --- Paid Leave Management ---
    leave_ids = fields.One2many('custom.leave', 'employee_id', string='Congés')
    
    annual_leave_quota = fields.Integer(string='Quota Annuel', compute='_compute_leave_stats')
    leaves_taken = fields.Float(string='Congés Pris (Année courante)', compute='_compute_leave_stats')
    leaves_remaining = fields.Float(string='Solde Restant', compute='_compute_leave_stats')
    
    @api.depends('leave_ids.state', 'leave_ids.days_count', 'leave_ids.leave_type')
    def _compute_leave_stats(self):
        from datetime import date
        current_year = date.today().year
        config = self.env['custom.attendance.config'].get_main_config()
        quota = config.annual_leave_quota if config else 18
        
        for rec in self:
            rec.annual_leave_quota = quota
            
            # Sum approved paid leaves in the current year
            taken = sum(l.days_count for l in rec.leave_ids 
                        if l.state == 'approved' 
                        and l.leave_type == 'paid'
                        and l.date_from.year == current_year)
            
            rec.leaves_taken = taken
            rec.leaves_remaining = quota - taken
