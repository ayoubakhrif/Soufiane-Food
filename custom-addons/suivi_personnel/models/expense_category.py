from odoo import models, fields
from datetime import date, timedelta

class ExpenseCategory(models.Model):
    _name = 'suivi.expense.category'
    _description = 'Catégorie de Dépense'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Actif', default=True)
    monthly_limit = fields.Float(
        string='Limite mensuelle',
        help='Le montant maximum à dépenser par mois'
    )
    is_daily = fields.Boolean(
        string='Journalière/Mensuelle',
        help='Siu séléctionné la limite mensuelle sera divisé par jour'
    )
    current_balance = fields.Float(
        string='Situation actuelle',
        compute='_compute_current_situation'
    )

    limit_exceeded = fields.Boolean(
        string='Limite dépassée',
        compute='_compute_current_situation'
    )

    def _get_month_period(self):
        config = self.env['suivi.config'].get_config()
        start_day = config.month_start_day or 1

        today = date.today()

        if today.day < start_day:
            month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=start_day)
        else:
            month_start = today.replace(day=start_day)

        return month_start, today
    
    @api.depends('monthly_limit', 'is_daily')
    def _compute_current_situation(self):
        Expense = self.env['suivi.expense.daily']

        for category in self:
            month_start, today = category._get_month_period()

            expenses = Expense.search([
                ('category_id', '=', category.id),
                ('date', '>=', month_start),
                ('date', '<=', today),
            ])

            total_spent = sum(expenses.mapped('amount'))

            if not category.monthly_limit:
                category.current_balance = 0.0
                category.limit_exceeded = False
                continue

            # 🔹 Catégorie journalière
            if category.is_daily:
                days_passed = (today - month_start).days + 1
                daily_limit = category.monthly_limit / 30.0
                allowed_until_today = daily_limit * days_passed
            else:
                # 🔹 Catégorie mensuelle
                allowed_until_today = category.monthly_limit

            category.current_balance = allowed_until_today - total_spent
            category.limit_exceeded = category.current_balance < 0
