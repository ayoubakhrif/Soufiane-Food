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
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With'),
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

        # Dépenses dans la période
        expenses = request.env['suivi.expense.daily'].sudo().search([
            ('date', '>=', date_start),
            ('date', '<=', date_end)
        ])
        total_spent = sum(expenses.mapped('amount'))

        # Catégories & Objectifs
        categories = request.env['suivi.expense.category'].sudo().search([('active', '=', True)], order='name asc')
        categories_data = []
        total_budget = 0.0

        for cat in categories:
            cat_expenses = expenses.filtered(lambda e: e.category_id.id == cat.id)
            spent = sum(cat_expenses.mapped('amount'))
            limit = cat.get_monthly_limit_for_period(period) or 0.0

            has_objective = (limit > 0)
            if has_objective:
                total_budget += limit
                remaining = limit - spent
                pct = (spent / limit * 100) if limit > 0 else 0.0
            else:
                remaining = 0.0
                pct = 0.0

            categories_data.append({
                'id': cat.id,
                'name': cat.name,
                'has_objective': has_objective,
                'limit': round(limit, 2),
                'spent': round(spent, 2),
                'remaining': round(remaining, 2),
                'percentage': round(pct, 1),
                'is_exceeded': spent > limit if has_objective else False,
            })

        total_remaining = total_budget - total_spent
        daily_advised = round(total_remaining / days_remaining, 2) if (total_remaining > 0 and days_remaining > 0) else 0.0
        global_pct = round((total_spent / total_budget * 100), 1) if total_budget > 0 else 0.0

        # Dernières dépenses récentes (5)
        recent_records = expenses.sorted(key=lambda r: (str(r.date), r.id), reverse=True)[:5]
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
                    'budget_total': round(total_budget, 2),
                    'spent_total': round(total_spent, 2),
                    'remaining_total': round(total_remaining, 2),
                    'daily_advised': daily_advised,
                    'percentage': global_pct,
                    'is_exceeded': total_spent > total_budget if total_budget > 0 else False,
                },
                'categories': categories_data,
                'recent_expenses': recent_expenses,
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
                ('Access-Control-Allow-Origin', '*'),
                ('Cache-Control', 'max-age=3600'),
            ]
            return request.make_response(image_data, headers=headers)
        except Exception:
            return request.not_found()
