from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import date

class SuiviMonthReport(models.Model):
    _name = 'suivi.month.report'
    _description = 'Rapport Mensuel'
    _order = 'date_start desc'

    period_id = fields.Many2one('suivi.period', string='Période', required=True, readonly=True, states={'draft': [('readonly', False)]})
    name = fields.Char(string='Libellé', compute='_compute_period_details', store=True)
    date_start = fields.Date(string='Date Début', compute='_compute_period_details', store=True)
    date_end = fields.Date(string='Date Fin', compute='_compute_period_details', store=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Validé')
    ], string='État', default='draft', tracking=True)

    # Incomes
    income_fixed = fields.Float(string='Revenus Fixes', readonly=True, states={'draft': [('readonly', False)]}) # Can be Computed or editable? Plan said sum. Let's make it computed but storeable.
    income_daily = fields.Float(string='Revenus Journaliers', readonly=True)
    income_total = fields.Float(string='Total Revenus', compute='_compute_totals', store=True)

    # Expenses
    expense_fixed = fields.Float(string='Dépenses Fixes', readonly=True)
    expense_daily = fields.Float(string='Dépenses Journalières', readonly=True)
    expense_total = fields.Float(string='Total Dépenses', compute='_compute_totals', store=True)

    # Result
    balance = fields.Float(string='Solde (Revenus - Dépenses)', compute='_compute_totals', store=True)

    line_ids = fields.One2many('suivi.month.report.line', 'report_id', string='Détail par Catégorie', readonly=True)

    @api.depends('period_id')
    def _compute_period_details(self):
        for rec in self:
            if rec.period_id:
                rec.name = f"Rapport Mensuel - {rec.period_id.name}"
                rec.date_start = rec.period_id.date_start
                rec.date_end = rec.period_id.date_end
            else:
                rec.name = False
                rec.date_start = False
                rec.date_end = False

    @api.depends('income_fixed', 'income_daily', 'expense_fixed', 'expense_daily')
    def _compute_totals(self):
        for rec in self:
            rec.income_total = rec.income_fixed + rec.income_daily
            rec.expense_total = rec.expense_fixed + rec.expense_daily
            rec.balance = rec.income_total - rec.expense_total

    def action_compute(self):
        self.ensure_one()
        # 1. Calculate Fixed Income (All active monthly incomes)
        # Assuming monthly incomes are recurrent and apply to every month
        monthly_incomes = self.env['suivi.income.monthly'].search([])
        income_fixed_total = sum(monthly_incomes.mapped('amount'))

        # 2. Calculate Daily Income (In period)
        daily_incomes = self.env['suivi.income.daily'].search([
            ('date', '>=', self.date_start),
            ('date', '<=', self.date_end)
        ])
        income_daily_total = sum(daily_incomes.mapped('amount'))

        # 3. Calculate Fixed Expenses (All active monthly expenses)
        monthly_expenses = self.env['suivi.expense.monthly'].search([])
        expense_fixed_total = sum(monthly_expenses.mapped('amount'))

        # 4. Calculate Daily Expenses (In period) & Lines
        daily_expenses = self.env['suivi.expense.daily'].search([
            ('date', '>=', self.date_start),
            ('date', '<=', self.date_end)
        ])
        expense_daily_total = sum(daily_expenses.mapped('amount'))

        # 5. Generate Lines for Categories
        categories = self.env['suivi.expense.category'].search([])
        
        # Clear existing lines
        self.line_ids.unlink()
        
        lines_to_create = []
        for cat in categories:
            # Filter expenses for this category in the period
            cat_expenses = daily_expenses.filtered(lambda e: e.category_id == cat)
            spent = sum(cat_expenses.mapped('amount'))
            
            # Using monthly limit from category definition
            limit = cat.monthly_limit
            remaining = limit - spent

            lines_to_create.append({
                'report_id': self.id,
                'category_id': cat.id,
                'limit': limit,
                'spent': spent,
                'remaining': remaining,
            })
        
        self.env['suivi.month.report.line'].create(lines_to_create)

        # Update main record
        self.write({
            'income_fixed': income_fixed_total,
            'income_daily': income_daily_total,
            'expense_fixed': expense_fixed_total,
            'expense_daily': expense_daily_total,
        })
    
    def action_validate(self):
        self.write({'state': 'done'})

    def action_draft(self):
        self.write({'state': 'draft'})


class SuiviMonthReportLine(models.Model):
    _name = 'suivi.month.report.line'
    _description = 'Ligne de Rapport Mensuel'
    _order = 'remaining asc' # Show exceeded first

    report_id = fields.Many2one('suivi.month.report', string='Rapport', ondelete='cascade')
    category_id = fields.Many2one('suivi.expense.category', string='Catégorie')
    limit = fields.Float(string='Limite')
    spent = fields.Float(string='Dépensé')
    remaining = fields.Float(string='Restant')
