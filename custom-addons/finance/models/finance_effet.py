from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class FinanceEffet(models.Model):
    _name = 'finance.effet'
    _description = 'Finance Effet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'serie'

    # Required Fields
    emitter = fields.Selection([
        ('nawfal', 'Nawfal'),
        ('dahrouch', 'Dahrouch'),
        ('talon', 'Talon')
    ], string='Émetteur', required=True, tracking=True)
    
    serie = fields.Char(string='Série / Référence', required=True, tracking=True)
    
    date_emission = fields.Date(string='Date d’émission', required=True, default=fields.Date.context_today, tracking=True)
    date_echeance = fields.Date(string='Date d’échéance', required=True, tracking=True)
    date_encaissement = fields.Date(string='Date d’encaissement', tracking=True)
    
    ste_id = fields.Many2one('finance.ste', string='Société', required=True, tracking=True)
    benif_id = fields.Many2one('finance.benif', string='Bénificiaire', required=True, tracking=True)
    
    montant = fields.Float(string='Montant', required=True, tracking=True)
    comment = fields.Text(string='Commentaire', tracking=True)

    # Computed Fields
    state = fields.Selection([
        ('encaisse', 'Encaissé'),
        ('non_encaisse', 'Non encaissé'),
    ], string='État', compute='_compute_state', store=True, tracking=True)

    # Business Logic
    @api.depends('date_encaissement')
    def _compute_state(self):
        for rec in self:
            if rec.date_encaissement:
                rec.state = 'encaisse'
            else:
                rec.state = 'non_encaisse'

    # Constraints
    @api.constrains('montant')
    def _check_amount(self):
        for rec in self:
            if rec.montant <= 0:
                raise ValidationError("Le montant doit être supérieur à 0.")

    @api.constrains('date_emission', 'date_echeance')
    def _check_dates(self):
        for rec in self:
            if rec.date_emission and rec.date_echeance and rec.date_echeance < rec.date_emission:
                raise ValidationError("La date d’échéance ne peut pas être antérieure à la date d’émission.")

    _sql_constraints = [
        ('unique_serie_ste', 'unique(serie, ste_id)', 'La référence (Série) doit être unique par société.')
    ]
