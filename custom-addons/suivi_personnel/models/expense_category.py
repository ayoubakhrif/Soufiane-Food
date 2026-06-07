from odoo import models, fields, api
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

class ExpenseCategoryObjective(models.Model):
    _name = 'suivi.expense.category.objective'
    _description = 'Objectif Mensuel de Catégorie'
    
    category_id = fields.Many2one('suivi.expense.category', string='Catégorie', required=True, ondelete='cascade')
    period_id = fields.Many2one('suivi.period', string='Période', required=True)
    amount = fields.Float(string='Objectif Mensuel', required=True)

    _sql_constraints = [
        ('category_period_uniq', 'unique(category_id, period_id)', 'Il ne peut y avoir qu\'un seul objectif par période pour une catégorie !')
    ]

class ExpenseCategory(models.Model):
    _name = 'suivi.expense.category'
    _description = 'Catégorie de Dépense'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Actif', default=True)
    monthly_limit = fields.Float(
        string='Limite mensuelle',
        help='Le montant maximum à dépenser par mois (Valeur par défaut)'
    )
    objective_ids = fields.One2many(
        'suivi.expense.category.objective', 
        'category_id', 
        string='Objectifs Mensuels'
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
    
    def get_monthly_limit_for_period(self, period=None):
        self.ensure_one()
        if not period:
            today = fields.Date.today()
            period = self.env['suivi.period'].search([
                ('date_start', '<=', today),
                ('date_end', '>=', today)
            ], limit=1)

        if period:
            objective = self.env['suivi.expense.category.objective'].search([
                ('category_id', '=', self.id),
                ('period_id', '=', period.id)
            ], limit=1)
            if objective:
                return objective.amount

        # fallback: first objective created/chronological
        if self.objective_ids:
            first_objective = self.objective_ids.sorted(lambda o: o.period_id.date_start)[0]
            return first_objective.amount

        return self.monthly_limit

    @api.depends('monthly_limit', 'objective_ids.amount', 'is_daily', 'expense_ids.amount', 'expense_ids.date')
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

            limit = category.get_monthly_limit_for_period()

            if not limit:
                category.current_balance = 0.0
                category.limit_exceeded = False
                continue

            # 🔹 Calcul Simplifié : Solde = Limite Mensuelle - Dépenses Totales
            category.current_balance = limit - total_spent
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
