from odoo import models, fields, api

class FinanceTalon(models.Model):
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

    used_chqs = fields.Integer(string='Nombre de chqs utilisés', compute='_compute_counts')
    unused_chqs = fields.Integer(string='Nombre de chqs restants', compute='_compute_counts')
    progress_html = fields.Html(string="Progression", compute="_compute_progress", sanitize=False)

    @api.depends('used_chqs', 'num_chq')
    def _compute_progress(self):
        for rec in self:
            if rec.num_chq:
                pct = int((rec.used_chqs / rec.num_chq) * 100)
            else:
                pct = 0

            # 🔥 Couleur dynamique
            if pct < 50:
                color = "#28a745"  # vert
            elif pct < 80:
                color = "#fd7e14"  # orange
            else:
                color = "#dc3545"  # rouge

            rec.progress_html = f"""
                <div style="width:100%; background:#e9ecef; border-radius:8px; height:18px;">
                    <div style="width:{pct}%; background:{color};
                                height:18px; border-radius:8px;">
                    </div>
                </div>
                <div style="font-size:12px; text-align:center; margin-top:3px; font-weight:600;">
                    {pct}% utilisé
                </div>
            """

    @api.depends('used_chqs', 'num_chq')
    def _compute_counts(self):
        for rec in self:
            rec.used_chqs = self.env['datacheque'].search_count([('talon_id', '=', rec.id)])
            rec.unused_chqs = rec.num_chq - rec.used_chqs
    