from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

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
        help='Si séléctionné la limite mensuelle sera divisé par jour'
    )
    current_balance = fields.Float(
        string='Situation actuelle',
        compute='_compute_current_situation',
        store=True
    )

    limit_exceeded = fields.Boolean(
        string='Limite dépassée',
        compute='_compute_current_situation',
        store=True
    )

    expense_ids = fields.One2many(
        'suivi.expense.daily', 
        'category_id', 
        string='Dépenses'
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
    
    @api.depends('monthly_limit', 'is_daily', 'expense_ids.amount', 'expense_ids.date')
    def _compute_current_situation(self):
        Expense = self.env['suivi.expense.daily']

        for category in self:
            month_start, month_end, today = category._get_month_bounds()

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

            # 🔹 Calcul Simplifié : Solde = Limite Mensuelle - Dépenses Totales
            category.current_balance = category.monthly_limit - total_spent
            category.limit_exceeded = category.current_balance < 0


    def _get_month_bounds(self):
        config = self.env['suivi.config'].get_config()
        start_day = config.month_start_day or 1
        today = date.today()
        # Début du mois comptable
        if today.day < start_day:
            month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=start_day)
        else:
            month_start = today.replace(day=start_day)

        # Fin du mois comptable = début + 1 mois - 1 jour
        month_end = month_start + relativedelta(months=1) - timedelta(days=1)

        return month_start, month_end, today

    @api.model
    def get_mobile_categories(self):
        """ Returns list of categories for the mobile app via RPC """
        categories = self.search([('active', '=', True)])
        return [{'id': cat.id, 'name': cat.name} for cat in categories]
