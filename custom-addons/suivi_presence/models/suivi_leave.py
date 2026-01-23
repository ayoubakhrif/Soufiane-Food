from odoo import models, fields, api, exceptions
from datetime import timedelta

class SuiviLeave(models.Model):
    _name = 'suivi.leave'
    _description = 'Demande de Congé (Suivi Présence)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'
    _order = 'date_from desc'

    employee_id = fields.Many2one('suivi.employee', string='Employé', required=True, tracking=True, ondelete='cascade')
    date_from = fields.Date(string='Date Début', required=True, tracking=True)
    date_to = fields.Date(string='Date Fin', required=True, tracking=True)
    
    leave_type = fields.Selection([
        ('paid', 'Congé Payé'),
        ('unpaid', 'Congé Sans Solde'),
        ('sick', 'Maladie'),
    ], string='Type de Congé', default='paid', required=True, tracking=True)
    
    reason = fields.Text(string='Motif')
    days_count = fields.Float(string='Jours Calculés', compute='_compute_days_count', store=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('approved', 'Approuvé'),
        ('refused', 'Refusé'),
    ], default='draft', string='Statut', tracking=True)
    
    @api.depends('date_from', 'date_to', 'employee_id')
    def _compute_days_count(self):
        config = self.env['suivi.config'].get_main_config()
        non_working_day = int(config.non_working_day) if config else 6
        holidays = config.public_holiday_ids.mapped('date') if config else []
        
        for rec in self:
            if not rec.date_from or not rec.date_to or rec.date_to < rec.date_from:
                rec.days_count = 0.0
                continue

            current_date = rec.date_from
            count = 0
            while current_date <= rec.date_to:
                if current_date.weekday() != non_working_day and current_date not in holidays:
                    count += 1
                current_date += timedelta(days=1)
            
            rec.days_count = count

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_overlap(self):
        for rec in self:
            domain = [
                ('id', '!=', rec.id),
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approved'),
                ('date_from', '<=', rec.date_to),
                ('date_to', '>=', rec.date_from),
            ]
            if self.search_count(domain) > 0:
                raise exceptions.ValidationError("Cet employé a déjà un congé approuvé sur cette période.")

    def action_approve(self):
        for rec in self:
            if rec.leave_type == 'paid':
                remaining = rec.employee_id.leaves_remaining
                if rec.days_count > remaining:
                    raise exceptions.ValidationError(f"Solde insuffisant ! Demandé: {rec.days_count}j, Restant: {remaining}j")
            rec.state = 'approved'

    def action_refuse(self):
        for rec in self:
            rec.state = 'refused'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
