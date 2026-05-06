# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TransportDriverBalanceArab(models.Model):
    _name = 'transport.driver.balance.arab'
    _description = 'تسوية حساب السائقين مقطورة'
    _rec_name = 'driver_id'
    _order = 'id desc'

    driver_id = fields.Many2one(
        'transport.driver',
        string='الشوفير / السائق',
        required=True,
        domain=[('remorque', '=', True)]
    )
    
    total_profit = fields.Float(
        string='إجمالي الأرباح',
        compute='_compute_totals',
        help="مجموع أرباح جميع رحلات هذا السائق"
    )
    total_paid = fields.Float(
        string='المبالغ المستلمة (المدفوعة)',
        compute='_compute_totals',
        help="مجموع المبالغ التي تم دفعها وتسجيلها في الجدول أدناه"
    )
    total_unpaid = fields.Float(
        string='المبالغ غير المدفوعة (المتبقية)',
        compute='_compute_totals',
        help="المبالغ المتبقية في حساب السائق (إجمالي الأرباح - المبالغ المستلمة)"
    )

    payment_line_ids = fields.One2many(
        'transport.driver.payment.line.arab',
        'balance_id',
        string='سجل الدفعات'
    )

    _sql_constraints = [
        ('driver_uniq', 'unique(driver_id)', 'يوجد بالفعل حساب مفتوح لهذا السائق!')
    ]

    @api.depends('driver_id', 'payment_line_ids.amount')
    def _compute_totals(self):
        for rec in self:
            if rec.driver_id:
                # Sum profit of all transport.trip.remorque.arab for this driver
                trips = self.env['transport.trip.remorque.arab'].search([
                    ('driver_remorque_id', '=', rec.driver_id.id)
                ])
                rec.total_profit = sum(trips.mapped('profit'))
                
                # Sum of entered payments
                rec.total_paid = sum(rec.payment_line_ids.mapped('amount'))
                
                # Unpaid = profit - paid
                rec.total_unpaid = rec.total_profit - rec.total_paid
            else:
                rec.total_profit = 0.0
                rec.total_paid = 0.0
                rec.total_unpaid = 0.0


class TransportDriverPaymentLineArab(models.Model):
    _name = 'transport.driver.payment.line.arab'
    _description = 'سطر دفعات حساب السائق مقطورة'
    _order = 'date desc, id desc'

    balance_id = fields.Many2one(
        'transport.driver.balance.arab',
        string='الحساب',
        ondelete='cascade',
        required=True
    )
    date = fields.Date(
        string='التاريخ',
        default=fields.Date.context_today,
        required=True
    )
    amount = fields.Float(
        string='المبلغ المدفوع',
        required=True
    )
    note = fields.Char(
        string='ملاحظة'
    )

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("يجب أن يكون مبلغ الدفعة أكبر من الصفر."))
