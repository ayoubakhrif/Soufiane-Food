from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import date

class SuiviConfig(models.Model):
    _name = 'suivi.config'
    _description = 'Suivi Personnel Configuration'

    name = fields.Char(string='Configuration', default='Paramètres', required=True)
    month_start_day = fields.Integer(
        string='Jour de début du mois',
        default=1,
        required=True,
        help="Définit le jour du mois où commence la période comptable (ex: 1, 2, 15, etc.)"
    )

    @api.model
    def get_config(self):
        """Retrieve or create the singleton configuration record"""
        config = self.search([], limit=1)
        if not config:
            config = self.create({'name': 'Paramètres', 'month_start_day': 1})
        return config

    @api.constrains('month_start_day')
    def _check_month_start_day(self):
        for rec in self:
            if rec.month_start_day < 1 or rec.month_start_day > 31:
                raise models.ValidationError("Le jour de début doit être entre 1 et 31")

    def write(self, vals):
        res = super(SuiviConfig, self).write(vals)
        if 'month_start_day' in vals:
            self._update_all_periods_and_records()
        return res

    def _update_all_periods_and_records(self):
        """
        When configuration changes, we must:
        1. Update dates of all existing periods.
        2. Recompute period assignment for all expenses and incomes.
        """
        start_day = self.month_start_day
        periods = self.env['suivi.period'].search([])
        
        # 1. Update Periods
        for period in periods:
            # Name format expected: YYYY-MM
            try:
                year, month = map(int, period.name.split('-'))
                # Handle edge cases for short months if start_day is 31, but for period Start Date logic,
                # usually accounting periods starting on 31st are tricky. 
                # Assuming standard behavior: replace(day=start_day)
                # If start_day is > days in month, simple replace might fail. 
                # Let's use robust date creation.
                
                # Determining the start date of this period name (YYYY-MM)
                # If start_day is 1, it matches YYYY-MM-01.
                # If start_day is 15, it matches YYYY-MM-15.
                
                try:
                    new_start = date(year, month, start_day)
                except ValueError:
                    # Fallback for short months (e.g. Feb 30) -> Last day of month
                    last_day_of_month = date(year, month, 1) + relativedelta(months=1) - relativedelta(days=1)
                    new_start = last_day_of_month
                
                # End date is always Start + 1 Month - 1 Day
                new_end = new_start + relativedelta(months=1) - relativedelta(days=1)
                
                period.write({
                    'date_start': new_start,
                    'date_end': new_end
                })
            except ValueError:
                continue # Skip periods with non-standard names

        # 2. Recompute Records
        # Force recomputation of _compute_period
        self.env['suivi.expense.daily'].search([])._compute_period()
        self.env['suivi.income.daily'].search([])._compute_period()

        # 3. Recompute Reports
        # Force recomputation of dates and name for reports
        self.env['suivi.month.report'].search([])._compute_period_details()

    def open_settings(self):
        """Helper to open the form view of the singleton"""
        config = self.get_config()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Paramètres Généraux',
            'res_model': 'suivi.config',
            'res_id': config.id,
            'view_mode': 'form',
            'target': 'inline',
        }

    @api.model
    def create_mobile_transaction(self, vals):
        """ Creates a transaction from mobile app via RPC """
        trans_type = vals.get('type')
        if trans_type == 'expense':
            return self.env['suivi.expense.daily'].create({
                'amount': vals.get('amount'),
                'date': vals.get('date', fields.Date.today()),
                'category_id': vals.get('category_id'),
                'description': vals.get('description'),
            }).id
        elif trans_type == 'income':
            return self.env['suivi.income.daily'].create({
                'amount': vals.get('amount'),
                'date': vals.get('date', fields.Date.today()),
                'description': vals.get('description'),
            }).id
        return False

    @api.model
    def get_recent_transactions(self, limit=10):
        """ Returns last N transactions for mobile app via RPC """
        expenses = self.env['suivi.expense.daily'].search([], limit=limit, order='date desc, id desc')
        incomes = self.env['suivi.income.daily'].search([], limit=limit, order='date desc, id desc')
        
        combined = []
        for exp in expenses:
            combined.append({
                'type': 'expense',
                'date': exp.date,
                'amount': exp.amount,
                'category': exp.category_id.name,
                'description': exp.description or '',
            })
        for inc in incomes:
            combined.append({
                'type': 'income',
                'date': inc.date,
                'amount': inc.amount,
                'category': 'Revenu',
                'description': inc.description or '',
            })
        combined.sort(key=lambda x: str(x['date']), reverse=True)
        return combined[:limit]
