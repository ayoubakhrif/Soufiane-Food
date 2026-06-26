from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from calendar import monthrange

class TransportTripRemorqueArab(models.Model):
    _name = 'transport.trip.remorque.arab'
    _description = 'رحلة نقل مقطورة'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    date = fields.Date(string='تاريخ الرحلة', required=True, default=fields.Date.context_today)
    driver_remorque_id = fields.Many2one(
        'transport.driver', 
        string='السائق', 
        required=True, 
        tracking=True, 
        domain=[('remorque', '=', True)]
    )
    # Deprecated fields (kept for data safety, but hidden in views)
    driver = fields.Char(string='السائق (قديم)')
    client = fields.Char(string='الزبون (قديم)')
    
    destination = fields.Selection([
        ('tanger', 'طنجة'),
        ('fenideq', 'الفنيدق'),
        ('tetouan', 'تطوان'),
        ('casablanca', 'الدار البيضاء'),
    ], string='الوجهة', tracking=True)
    charge_fuel = fields.Float(string='المازوت', tracking=True)
    charge_driver = fields.Float(string='مصاريف السائق', tracking=True)
    charge_adblue = fields.Float(string='AdBlue', tracking=True)
    charge_mixed = fields.Float(string='مصاريف متنوعة (تحدد في الملاحظات)', tracking=True)
    note = fields.Text(string='ملاحظة (مصاريف متنوعة)')
    going_price = fields.Float(string='سعر الذهاب', tracking=True)
    profit = fields.Float(
        string='الربح',
        compute='_compute_profit',
        store=True,
        tracking=True
    )
    profit_paid = fields.Float(
        string='الربح المدفوع',
        compute='_compute_split_profits',
        store=True,
        tracking=True
    )
    profit_unpaid = fields.Float(
        string='الربح غير المدفوع',
        compute='_compute_split_profits',
        store=True,
        tracking=True
    )
    is_paid = fields.Boolean(string='مدفوع', default=False, tracking=True)
    payment_status = fields.Selection([
        ('paid', 'مدفوع'),
        ('unpaid', 'غير مدفوع')
    ], string='الحالة', compute='_compute_payment_status', store=True)
    is_checked = fields.Boolean(string="تم التحقق", default=False)
    total_amount = fields.Float(
        string='إجمالي المصاريف',
        compute='_compute_total_amount',
        store=True,
        tracking=True
    )

    def action_confirm_paid(self):
        for record in self:
            record.is_paid = True

    def action_set_unpaid(self):
        for record in self:
            record.is_paid = False

    @api.depends(
        'charge_fuel',
        'charge_driver',
        'charge_adblue',
        'charge_mixed'
    )
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = (
                (record.charge_fuel or 0.0) +
                (record.charge_driver or 0.0) +
                (record.charge_adblue or 0.0) +
                (record.charge_mixed or 0.0)
            )

    @api.depends('is_paid')
    def _compute_payment_status(self):
        for record in self:
            record.payment_status = 'paid' if record.is_paid else 'unpaid'

    @api.depends('going_price', 'total_amount')
    def _compute_profit(self):
        for rec in self:
            rec.profit = (rec.going_price or 0.0) - (rec.total_amount or 0.0)

    @api.depends('profit', 'is_paid')
    def _compute_split_profits(self):
        for rec in self:
            if rec.is_paid:
                rec.profit_paid = rec.profit
                rec.profit_unpaid = 0.0
            else:
                rec.profit_paid = 0.0
                rec.profit_unpaid = rec.profit

    @api.constrains('charge_mixed', 'note')
    def _check_mixed_note(self):
        for rec in self:
            if rec.charge_mixed > 0 and not rec.note:
                raise ValidationError(_("يرجى تحديد ملاحظة للمصاريف المتنوعة."))

    @api.model
    def create(self, vals):
        record = super().create(vals)
        return record
    
    def write(self, vals):
        res = super().write(vals)
        return res

    def unlink(self):
        res = super().unlink()
        return res
