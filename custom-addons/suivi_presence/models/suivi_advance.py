from odoo import models, fields, api, exceptions

class SuiviSalaryAdvance(models.Model):
    _name = 'suivi.salary.advance'
    _description = 'Avance sur Salaire'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    employee_id = fields.Many2one('suivi.employee', string='Employé', required=True, tracking=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Montant', required=True, tracking=True)
    reason = fields.Char(string='Motif')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé')
    ], string='Statut', default='draft', tracking=True)
    
    # Month/Year for deduction targeting
    month = fields.Selection([
        ('1', 'Janvier'), ('2', 'Février'), ('3', 'Mars'), ('4', 'Avril'),
        ('5', 'Mai'), ('6', 'Juin'), ('7', 'Juillet'), ('8', 'Aout'),
        ('9', 'Septembre'), ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre')
    ], string='Mois de déduction', compute='_compute_date_details', store=True, readonly=False)
    
    year = fields.Integer(string='Année de déduction', compute='_compute_date_details', store=True, readonly=False)

    @api.depends('date')
    def _compute_date_details(self):
        for rec in self:
            if rec.date:
                rec.month = str(rec.date.month)
                rec.year = rec.date.year

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
