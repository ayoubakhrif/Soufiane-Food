from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class IncomeDaily(models.Model):
    _name = 'suivi.income.daily'
    _description = 'Revenu Quotidien'
    _order = 'date desc, id desc'

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Montant', required=True)
    category = fields.Char(string='Catégorie')
    description = fields.Text(string='Description')
    
    # Computed fields for analysis
    month_period = fields.Char(
        string='Période',
        compute='_compute_period',
        store=True,
        index=True
    )
    year = fields.Integer(
        string='Année',
        compute='_compute_period',
        store=True,
        index=True
    )

    @api.depends('date')
    def _compute_period(self):
        for rec in self:
            if not rec.date:
                rec.month_period = False
                rec.year = False
                continue
            
            config = self.env['suivi.config'].get_config()
            start_day = config.month_start_day or 1
            
            if rec.date.day >= start_day:
                # Current month period
                period_date = rec.date
            else:
                # Previous month period
                period_date = rec.date - relativedelta(months=1)
            
            rec.month_period = period_date.strftime('%Y-%m')
            rec.year = period_date.year
