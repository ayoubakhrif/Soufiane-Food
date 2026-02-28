from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class ExpenseDaily(models.Model):
    _name = 'suivi.expense.daily'
    _description = 'Dépense Quotidienne'
    _order = 'date desc, id desc'

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Montant', required=True)
    category_id = fields.Many2one(
        'suivi.expense.category',
        string='Catégorie',
        required=True,
        ondelete='restrict'
    )
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
    period_id = fields.Many2one(
        'suivi.period',
        string='Période',
        compute='_compute_period',
        store=True,
        index=True
    )
    category_name = fields.Char(
        string='Catégorie',
        related='category_id.name',
        readonly=True
    )

    @api.depends('date')
    def _compute_period(self):
        for rec in self:
            if not rec.date:
                rec.month_period = False
                rec.year = False
                rec.period_id = False
                continue
            
            config = self.env['suivi.config'].get_config()
            start_day = config.month_start_day or 1
            
            if rec.date.day >= start_day:
                # Current month period
                period_date = rec.date
                month_start = rec.date.replace(day=start_day)
            else:
                # Previous month period
                period_date = rec.date - relativedelta(months=1)
                month_start = (rec.date - relativedelta(months=1)).replace(day=start_day)
            
            # Calculate Month End
            month_end = month_start + relativedelta(months=1) - relativedelta(days=1)

            period_name = period_date.strftime('%Y-%m')
            
            # Find or Create Period
            period = self.env['suivi.period'].search([('name', '=', period_name)], limit=1)
            if not period:
                period = self.env['suivi.period'].create({
                    'name': period_name,
                    'date_start': month_start,
                    'date_end': month_end,
                })

            rec.month_period = period_name
            rec.year = period_date.year
            rec.period_id = period.id
