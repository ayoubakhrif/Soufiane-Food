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
        ('sortie', 'Sortie'),
        ('absent', 'Absent')
    ], string='Type', required=True)
    
    absence_type = fields.Selection([
        ('deduction', 'Déduit du salaire'),
        ('leave', 'Consomme un jour de congé')
    ], string="Type d'absence")

    site = fields.Selection([
        ('mediouna', 'Mediouna'),
        ('casa', 'Casa')
    ], string='Site de Travail', required=True, default='mediouna')

    @api.onchange('employee_id')
    def _onchange_employee_site(self):
        if self.employee_id and self.employee_id.payroll_site:
            self.site = self.employee_id.payroll_site

    @api.model
    def create(self, vals):
        rec = super(SuiviPresence, self).create(vals)
        if rec.type == 'absent' and rec.absence_type == 'leave':
            # Create a Paid Leave
            # We assume 1 day duration for the absence date
            leave_vals = {
                'employee_id': rec.employee_id.id,
                'date_from': rec.datetime.date(),
                'date_to': rec.datetime.date(),
                'leave_type': 'paid',
                'reason': 'Absence marquée depuis le suivi de présence',
                'state': 'approved'
            }
            # Create and auto-approve
            self.env['suivi.leave'].create(leave_vals)
        return rec
