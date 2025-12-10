from odoo import models, fields

class FinanceSte(models.Model):
    _name = 'finance.talon'
    _description = 'Talons'
    _rec_name = 'name_shown'

    name = fields.Char(string='Talon', required=True)
    name_shown = fields.Char(string='Nom affiché', required=True)
    ste_id = fields.Many2one('finance.ste', string='Société', tracking=True, required=True)
    num_chq = fields.Integer(string='Nombres de chqs', required=True)
    serie = fields.Char(string='Série', required=True)
    etat = fields.Selection([
        ('actif', 'Actif'),
        ('cloture', 'Cloturé'),
        ('coffre', 'Coffre'),
    ], string='Etat', store=True)

    used_chqs = fields.Integer(string='Utilisés', compute='_compute_counts')
    unused_chqs = fields.Integer(string='Restants', compute='_compute_counts')

    def _compute_counts(self):
        for rec in self:
            rec.used_chqs = self.env['datacheque'].search_count([('talon_id', '=', rec.id)])
            rec.unused_chqs = rec.num_chq - rec.used_chqs
    