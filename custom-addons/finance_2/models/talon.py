from odoo import models, fields, api, _

class Finance2Talon(models.Model):
    _name = 'finance2.talon'
    _description = 'Talon de Chèques'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Référence Talon', required=True, tracking=True)
    ste_id = fields.Many2one('finance2.ste', string='Société', required=True, tracking=True)
    date_reception = fields.Date(string='Date de réception', tracking=True)
    
    first_cheque_number = fields.Char(string='Numéro de départ', required=True, tracking=True)
    num_chq = fields.Integer(string='Nombre de chèques', required=True, tracking=True, default=50)
    last_cheque_number = fields.Char(string='Numéro de fin', compute='_compute_last_cheque', store=True)
    
    etat = fields.Selection([
        ('coffre', 'En Coffre'),
        ('actif', 'Actif'),
        ('cloture', 'Clôturé'),
    ], string='État', default='coffre', compute='_compute_etat', store=True, readonly=False, tracking=True)

    cheque_ids = fields.One2many('finance2.cheque', 'talon_id', string='Chèques liés')
    
    used_chqs = fields.Integer(string='Utilisés', compute='_compute_metrics', store=True)
    unused_chqs = fields.Integer(string='Restants', compute='_compute_metrics', store=True)
    usage_percentage = fields.Float(string='% Utilisation', compute='_compute_metrics', store=True)
    last_used_chq = fields.Char(string='Dernier utilisé', compute='_compute_metrics', store=True)
    missing_chqs_text = fields.Text(string='Chèques manquants', compute='_compute_metrics', store=True)

    @api.depends('first_cheque_number', 'num_chq')
    def _compute_last_cheque(self):
        for rec in self:
            if rec.first_cheque_number and rec.first_cheque_number.isdigit() and rec.num_chq:
                length = len(rec.first_cheque_number)
                start_val = int(rec.first_cheque_number)
                end_val = start_val + rec.num_chq - 1
                rec.last_cheque_number = str(end_val).zfill(length)
            else:
                rec.last_cheque_number = False

    @api.depends('cheque_ids', 'cheque_ids.name', 'first_cheque_number', 'last_cheque_number')
    def _compute_metrics(self):
        for rec in self:
            cheques = rec.cheque_ids.filtered(lambda c: c.name and c.name.isdigit())
            rec.used_chqs = len(cheques)
            rec.unused_chqs = rec.num_chq - rec.used_chqs if rec.num_chq else 0
            rec.usage_percentage = (rec.used_chqs / rec.num_chq * 100) if rec.num_chq else 0.0
            
            if cheques:
                sorted_cheques = sorted([int(c.name) for c in cheques])
                rec.last_used_chq = str(sorted_cheques[-1]).zfill(len(rec.first_cheque_number or ''))
                
                # Check for missing
                if rec.first_cheque_number and rec.first_cheque_number.isdigit():
                    expected = set(range(int(rec.first_cheque_number), sorted_cheques[-1] + 1))
                    actual = set(sorted_cheques)
                    missing = sorted(list(expected - actual))
                    if missing:
                        rec.missing_chqs_text = ", ".join([str(m).zfill(len(rec.first_cheque_number)) for m in missing])
                    else:
                        rec.missing_chqs_text = False
                else:
                    rec.missing_chqs_text = False
            else:
                rec.last_used_chq = False
                rec.missing_chqs_text = False

    @api.depends('used_chqs', 'num_chq')
    def _compute_etat(self):
        for rec in self:
            if rec.used_chqs == 0:
                rec.etat = 'coffre'
            elif rec.used_chqs > 0 and rec.used_chqs < rec.num_chq:
                rec.etat = 'actif'
            elif rec.used_chqs >= rec.num_chq:
                rec.etat = 'cloture'
