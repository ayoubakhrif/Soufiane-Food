from odoo import models, fields, api

class SchoolPayment(models.Model):
    _name = 'school.payment'
    _description = 'School Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Payment Reference', required=True, copy=False, readonly=True, default='New')
    student_id = fields.Many2one('school.student', string='Student', required=True, tracking=True)
    parent_id = fields.Many2one('school.parent', related='student_id.parent_id', string='Parent', store=True, readonly=True)
    
    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    
    date = fields.Date(string='Payment Date', default=fields.Date.context_today, required=True)
    
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('mobile_money', 'Mobile Money')
    ], string='Payment Method', required=True, tracking=True)
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('school.payment') or 'New'
        return super(SchoolPayment, self).create(vals)

    def action_post(self):
        self.write({'status': 'posted'})
        
    def action_cancel(self):
        self.write({'status': 'cancelled'})
        
    def action_draft(self):
        self.write({'status': 'draft'})
