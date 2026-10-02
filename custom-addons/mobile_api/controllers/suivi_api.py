# -*- coding: utf-8 -*-
import json
import logging
import base64
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class MobileSuiviController(http.Controller):

    def _json_response(self, data, status=200):
        headers = [
            ('Content-Type', 'application/json'),
        ]
        return request.make_response(
            json.dumps(data, ensure_ascii=False, default=str),
            headers=headers,
            status=status
        )

    def _get_request_data(self):
        try:
            if request.httprequest.data:
                return json.loads(request.httprequest.data.decode('utf-8'))
        except Exception:
            pass
        return request.params or {}

    def _get_active_period_info(self):
        """
        Dynamically calculates the current period according to suivi.config (month_start_day)
        """
        config = request.env['suivi.config'].sudo().get_config()
        start_day = config.month_start_day or 1
        today = fields.Date.today()

        # Compute period bounds based on start_day
        if today.day >= start_day:
            try:
                month_start = today.replace(day=start_day)
            except ValueError:
                month_start = today.replace(day=28)
        else:
            prev_month_last = today.replace(day=1) - timedelta(days=1)
            try:
                month_start = prev_month_last.replace(day=start_day)
            except ValueError:
                month_start = prev_month_last.replace(day=28)

        month_end = month_start + relativedelta(months=1) - timedelta(days=1)
        period_name = month_start.strftime('%Y-%m')

        # Find or create period
        period = request.env['suivi.period'].sudo().search([
            ('date_start', '<=', today),
            ('date_end', '>=', today)
        ], limit=1)

        if not period:
            period = request.env['suivi.period'].sudo().search([('name', '=', period_name)], limit=1)
            if not period:
                period = request.env['suivi.period'].sudo().create({
                    'name': period_name,
                    'date_start': month_start,
                    'date_end': month_end,
                })
            else:
                period.sudo().write({'date_start': month_start, 'date_end': month_end})

        days_remaining = max(1, (month_end - today).days + 1)
        total_days = max(1, (month_end - month_start).days + 1)

        return {
            'period': period,
            'period_name': period.name,
            'month_start_day': start_day,
            'date_start': month_start.strftime('%Y-%m-%d'),
            'date_end': month_end.strftime('%Y-%m-%d'),
            'today': today.strftime('%Y-%m-%d'),
            'days_remaining': days_remaining,
            'total_days': total_days,
        }

    # =========================================================================
    # 🔑 AUTHENTICATION
    # =========================================================================
    @http.route('/api/suivi/login', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_login(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        data = self._get_request_data()
        login = (data.get('login') or data.get('username') or '').strip()
        password = (data.get('password') or '').strip()

        if not login or not password:
            return self._json_response({
                'status': 'error',
                'message': 'Veuillez renseigner votre identifiant et votre mot de passe.'
            }, status=400)

        db = request.env.cr.dbname
        try:
            uid = request.session.authenticate(db, login, password)
            if uid:
                user = request.env['res.users'].sudo().browse(uid)
                return self._json_response({
                    'status': 'success',
                    'user': {
                        'id': user.id,
                        'name': user.name,
                        'login': user.login,
                    }
                })
        except Exception as e:
            _logger.warning("Échec de connexion utilisateur Odoo: %s", str(e))

        return self._json_response({
            'status': 'error',
            'message': 'Identifiant ou mot de passe incorrect.'
        }, status=401)

    # =========================================================================
    # 📊 DASHBOARD & OBJECTIVES
    # =========================================================================
    @http.route('/api/suivi/dashboard', type='http', auth='public', methods=['GET', 'POST', 'OPTIONS'], csrf=False, cors='*')
    def api_dashboard(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        period_info = self._get_active_period_info()
        period = period_info['period']
        date_start = period_info['date_start']
        date_end = period_info['date_end']
        days_remaining = period_info['days_remaining']

        # 1. Utilisation du rapport officiel Odoo (suivi.month.report)
        ReportModel = request.env['suivi.month.report'].sudo()
        report = ReportModel.search([('period_id', '=', period.id)], limit=1)
        if not report:
            report = ReportModel.create({'period_id': period.id})
        report.action_compute()

        # 2. Dépenses Mensuelles Fixes (Détail)
        monthly_expenses_records = request.env['suivi.expense.monthly'].sudo().search([], order='category asc')
        monthly_expenses_data = [{
            'id': m.id,
            'name': m.name or m.category or 'Charge fixe',
            'category': m.category or '',
            'amount': round(m.amount, 2),
            'description': m.description or '',
        } for m in monthly_expenses_records]

        # 3. Catégories & Objectifs depuis les lignes officielles du rapport
        categories_data = []
        for line in report.line_ids:
            limit = line.limit or 0.0
            spent = line.spent or 0.0
            remaining = line.remaining or 0.0
            has_obj = (limit > 0)
            pct = (spent / limit * 100) if limit > 0 else 0.0

            categories_data.append({
                'id': line.category_id.id,
                'name': line.category_id.name,
                'has_objective': has_obj,
                'limit': round(limit, 2),
                'spent': round(spent, 2),
                'remaining': round(remaining, 2),
                'percentage': round(pct, 1),
                'is_exceeded': remaining < 0,
            })

        # 4. Totaux financiers officiels (exactement identiques au rapport Odoo)
        income_total = report.income_total or 0.0
        income_fixed = report.income_fixed or 0.0
        income_daily = report.income_daily or 0.0
        expense_total = report.expense_total or 0.0
        expense_fixed = report.expense_fixed or 0.0
        expense_daily = report.expense_daily or 0.0
        balance = report.balance or 0.0 # Solde net: Revenus - Dépenses

        # Budget de référence : Revenus du mois (ou somme des limites si aucun revenu n'est défini)
        sum_category_limits = sum(c['limit'] for c in categories_data if c['has_objective'])
        budget_reference = income_total if income_total > 0 else sum_category_limits
        global_pct = round((expense_total / budget_reference * 100), 1) if budget_reference > 0 else 0.0
        daily_advised = round(balance / days_remaining, 2) if (balance > 0 and days_remaining > 0) else 0.0

        # 5. Dernières dépenses récentes (5)
        recent_records = request.env['suivi.expense.daily'].sudo().search([
            ('date', '>=', date_start),
            ('date', '<=', date_end)
        ], limit=5, order='date desc, id desc')

        recent_expenses = []
        for exp in recent_records:
            recent_expenses.append({
                'id': exp.id,
                'date': exp.date,
                'amount': exp.amount,
                'category_id': exp.category_id.id,
                'category_name': exp.category_id.name,
                'description': exp.description or '',
                'has_receipt': bool(exp.has_receipt),
            })

        return self._json_response({
            'status': 'success',
            'data': {
                'period': {
                    'name': period_info['period_name'],
                    'date_start': date_start,
                    'date_end': date_end,
                    'month_start_day': period_info['month_start_day'],
                    'days_remaining': days_remaining,
                    'total_days': period_info['total_days'],
                },
                'totals': {
                    'income_total': round(income_total, 2),
                    'income_fixed': round(income_fixed, 2),
                    'income_daily': round(income_daily, 2),
                    'budget_total': round(budget_reference, 2),
                    'spent_total': round(expense_total, 2),
                    'expense_fixed_total': round(expense_fixed, 2),
                    'expense_daily_total': round(expense_daily, 2),
                    'remaining_total': round(balance, 2),
                    'daily_advised': daily_advised,
                    'percentage': global_pct,
                    'is_exceeded': balance < 0,
                },
                'categories': categories_data,
                'recent_expenses': recent_expenses,
                'monthly_expenses': monthly_expenses_data,
            }
        })

    # =========================================================================
    # 📑 CATEGORIES LIST
    # =========================================================================
    @http.route('/api/suivi/categories', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_categories(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        categories = request.env['suivi.expense.category'].sudo().search([('active', '=', True)], order='name asc')
        data = [{
            'id': c.id,
            'name': c.name,
            'monthly_limit': c.monthly_limit or 0.0,
        } for c in categories]

        return self._json_response({'status': 'success', 'data': data})

    # =========================================================================
    # ➕ CREATE EXPENSE (SORTIE JOURNALIÈRE)
    # =========================================================================
    @http.route('/api/suivi/expense/create', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_create_expense(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        data = self._get_request_data()
        amount_raw = data.get('amount')
        category_id = data.get('category_id')
        expense_date = data.get('date') or fields.Date.today()
        description = data.get('description') or ''
        receipt_image_b64 = data.get('receipt_image') # Base64 string
        receipt_filename = data.get('receipt_filename') or 'receipt.jpg'

        is_monthly = data.get('is_monthly') == True or data.get('type') == 'monthly'

        if is_monthly:
            if not amount_raw:
                return self._json_response({
                    'status': 'error',
                    'message': 'Le montant est obligatoire.'
                }, status=400)
            
            try:
                amount = float(amount_raw)
                if amount <= 0:
                    return self._json_response({
                        'status': 'error',
                        'message': 'Le montant doit être supérieur à zéro.'
                    }, status=400)
            except (ValueError, TypeError):
                return self._json_response({
                    'status': 'error',
                    'message': 'Montant invalide.'
                }, status=400)

            category_name = data.get('category_name') or ''
            if not category_name and category_id:
                cat = request.env['suivi.expense.category'].sudo().browse(int(category_id))
                if cat.exists():
                    category_name = cat.name
            if not category_name:
                category_name = description or 'Charge mensuelle'

            vals = {
                'category': category_name,
                'amount': amount,
                'description': description.strip(),
            }

            try:
                rec = request.env['suivi.expense.monthly'].sudo().create(vals)
                return self._json_response({
                    'status': 'success',
                    'message': 'Charge mensuelle enregistrée avec succès.',
                    'id': rec.id,
                })
            except Exception as e:
                _logger.exception("Erreur création charge mensuelle: %s", str(e))
                return self._json_response({
                    'status': 'error',
                    'message': f"Erreur lors de l'enregistrement: {str(e)}"
                }, status=500)

        # Sinon : Dépense Quotidienne
        if not amount_raw or not category_id:
            return self._json_response({
                'status': 'error',
                'message': 'Le montant et la catégorie sont obligatoires.'
            }, status=400)

        try:
            amount = float(amount_raw)
            if amount <= 0:
                return self._json_response({
                    'status': 'error',
                    'message': 'Le montant doit être supérieur à zéro.'
                }, status=400)
        except (ValueError, TypeError):
            return self._json_response({
                'status': 'error',
                'message': 'Montant invalide.'
            }, status=400)

        # Nettoyage Base64 si préfixe data:image/...;base64,
        if receipt_image_b64 and ',' in receipt_image_b64:
            receipt_image_b64 = receipt_image_b64.split(',', 1)[1]

        vals = {
            'amount': amount,
            'category_id': int(category_id),
            'date': expense_date,
            'description': description.strip(),
        }

        if receipt_image_b64:
            vals['receipt_image'] = receipt_image_b64
            vals['receipt_filename'] = receipt_filename

        try:
            rec = request.env['suivi.expense.daily'].sudo().create(vals)
            return self._json_response({
                'status': 'success',
                'message': 'Sortie enregistrée avec succès.',
                'id': rec.id,
            })
        except Exception as e:
            _logger.exception("Erreur lors de la création de la dépense: %s", str(e))
            return self._json_response({
                'status': 'error',
                'message': f"Erreur lors de l'enregistrement: {str(e)}"
            }, status=500)

    # =========================================================================
    # 📜 EXPENSES HISTORY
    # =========================================================================
    @http.route('/api/suivi/expenses', type='http', auth='public', methods=['GET', 'POST', 'OPTIONS'], csrf=False, cors='*')
    def api_expenses(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        params = self._get_request_data()
        category_id = params.get('category_id') or kwargs.get('category_id')
        limit = int(params.get('limit') or kwargs.get('limit') or 50)
        all_period = params.get('all_period') or kwargs.get('all_period')

        domain = []
        if not all_period:
            period_info = self._get_active_period_info()
            domain.append(('date', '>=', period_info['date_start']))
            domain.append(('date', '<=', period_info['date_end']))

        if category_id:
            domain.append(('category_id', '=', int(category_id)))

        records = request.env['suivi.expense.daily'].sudo().search(domain, limit=limit, order='date desc, id desc')
        
        result = []
        for exp in records:
            result.append({
                'id': exp.id,
                'date': exp.date,
                'amount': exp.amount,
                'category_id': exp.category_id.id,
                'category_name': exp.category_id.name,
                'description': exp.description or '',
                'has_receipt': bool(exp.has_receipt),
            })

        return self._json_response({'status': 'success', 'data': result})

    # =========================================================================
    # 🖼️ VIEW RECEIPT PHOTO
    # =========================================================================
    @http.route('/api/suivi/receipt/<int:expense_id>', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_get_receipt(self, expense_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        expense = request.env['suivi.expense.daily'].sudo().browse(expense_id)
        if not expense.exists() or not expense.receipt_image:
            return request.not_found()

        try:
            image_data = base64.b64decode(expense.receipt_image)
            headers = [
                ('Content-Type', 'image/jpeg'),
                ('Content-Length', str(len(image_data))),
                ('Cache-Control', 'max-age=3600'),
            ]
            return request.make_response(image_data, headers=headers)
        except Exception:
            return request.not_found()

    # =========================================================================
    # 📌 MONTHLY EXPENSES (CHARGES FIXES)
    # =========================================================================
    @http.route('/api/suivi/monthly_expenses', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_get_monthly_expenses(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        records = request.env['suivi.expense.monthly'].sudo().search([], order='category asc')
        data = [{
            'id': m.id,
            'name': m.name or m.category or 'Charge fixe',
            'category': m.category or '',
            'amount': round(m.amount, 2),
            'description': m.description or '',
        } for m in records]

        return self._json_response({'status': 'success', 'data': data})

    @http.route('/api/suivi/monthly_expense/delete/<int:expense_id>', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_delete_monthly_expense(self, expense_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})

        record = request.env['suivi.expense.monthly'].sudo().browse(expense_id)
        if not record.exists():
            return self._json_response({'status': 'error', 'message': 'Charge introuvable.'}, status=404)

        try:
            record.unlink()
            return self._json_response({'status': 'success', 'message': 'Charge mensuelle supprimée.'})
        except Exception as e:
            return self._json_response({'status': 'error', 'message': str(e)}, status=500)
