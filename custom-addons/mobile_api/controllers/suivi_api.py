from odoo import http, fields
from odoo.http import request
from datetime import date

class MobileSuiviController(http.Controller):

    @http.route('/mobile/suivi/dashboard', type='json', auth='user', methods=['POST'])
    def get_suivi_dashboard(self, **kwargs):
        """
        Returns summary stats for the current budget period.
        """
        today = fields.Date.today()
        # Find current period
        period = request.env['suivi.period'].search([
            ('date_start', '<=', today),
            ('date_end', '>=', today)
        ], limit=1)

        if not period:
            return {'status': 'error', 'message': 'Aucune période budgétaire trouvée pour aujourd\'hui.'}

        # Find or create report for this period
        report = request.env['suivi.month.report'].search([('period_id', '=', period.id)], limit=1)
        if not report:
            report = request.env['suivi.month.report'].create({'period_id': period.id})
        
        # Update report data to have latest stats
        report.action_compute()

        # Categories analysis
        categories_data = []
        for line in report.line_ids:
            categories_data.append({
                'id': line.category_id.id,
                'name': line.category_id.name,
                'limit': line.limit,
                'spent': line.spent,
                'remaining': line.remaining,
                'percentage': (line.spent / line.limit * 100) if line.limit > 0 else 0
            })

        return {
            'status': 'success',
            'data': {
                'period_name': period.name,
                'date_start': period.date_start,
                'date_end': period.date_end,
                'income_total': report.income_total,
                'expense_total': report.expense_total,
                'balance': report.balance,
                'categories': categories_data
            }
        }

    @http.route('/mobile/suivi/categories', type='json', auth='user', methods=['POST'])
    def get_suivi_categories(self, **kwargs):
        """ Returns list of expense categories """
        categories = request.env['suivi.expense.category'].search([])
        data = [{'id': cat.id, 'name': cat.name} for cat in categories]
        return {'status': 'success', 'data': data}

    @http.route('/mobile/suivi/transaction/create', type='json', auth='user', methods=['POST'])
    def create_suivi_transaction(self, **kwargs):
        """
        Creates an expense or income.
        Expected kwargs:
        - type: 'expense' or 'income'
        - amount: float
        - date: str (YYYY-MM-DD, optional, defaults to today)
        - category_id: int (required for expense)
        - description: str (optional)
        """
        trans_type = kwargs.get('type')
        amount = kwargs.get('amount')
        trans_date = kwargs.get('date', fields.Date.today())
        
        if not trans_type or not amount:
            return {'status': 'error', 'message': 'Paramètres manquants (type, amount).'}

        if trans_type == 'expense':
            cat_id = kwargs.get('category_id')
            if not cat_id:
                return {'status': 'error', 'message': 'Catégorie manquante pour une dépense.'}
            
            vals = {
                'amount': float(amount),
                'date': trans_date,
                'category_id': int(cat_id),
                'description': kwargs.get('description', '')
            }
            request.env['suivi.expense.daily'].create(vals)
        
        elif trans_type == 'income':
            vals = {
                'amount': float(amount),
                'date': trans_date,
                'description': kwargs.get('description', '')
            }
            request.env['suivi.income.daily'].create(vals)
        
        else:
            return {'status': 'error', 'message': 'Type de transaction invalide.'}

        return {'status': 'success', 'message': 'Transaction enregistrée avec succès.'}

    @http.route('/mobile/suivi/transactions/recent', type='json', auth='user', methods=['POST'])
    def get_recent_transactions(self, **kwargs):
        """ Returns the last 10 transactions """
        limit = int(kwargs.get('limit', 10))
        
        expenses = request.env['suivi.expense.daily'].search([], limit=limit, order='date desc, id desc')
        incomes = request.env['suivi.income.daily'].search([], limit=limit, order='date desc, id desc')
        
        combined = []
        for exp in expenses:
            combined.append({
                'type': 'expense',
                'id': exp.id,
                'date': exp.date,
                'amount': exp.amount,
                'category': exp.category_name,
                'description': exp.description or '',
            })
            
        for inc in incomes:
            combined.append({
                'type': 'income',
                'id': inc.id,
                'date': inc.date,
                'amount': inc.amount,
                'category': 'Revenu',
                'description': inc.description or '',
            })
            
        # Sort combined by date desc
        combined.sort(key=lambda x: str(x['date']), reverse=True)
        
        return {'status': 'success', 'data': combined[:limit]}
