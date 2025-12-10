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

    used_chqs = fields.Integer(string='Nombre de chqs utilisés', compute='_compute_counts', store=True)
    unused_chqs = fields.Integer(string='Nombre de chqs restants', compute='_compute_counts', store=True)
    usage_percentage = fields.Float(string='% Utilisation', compute='_compute_usage_percentage', store=True)
    
    cheque_ids = fields.One2many('datacheque', 'talon_id', string='Chèques')

    progress_html = fields.Html(string="Progression", compute="_compute_progress", sanitize=False)
    summary_card = fields.Html(string="Résumé", compute="_compute_card", sanitize=False)

    # -------------------------------------------------------------------
    # Résumé stylé (carte HTML)
    # -------------------------------------------------------------------
    @api.depends('used_chqs', 'unused_chqs', 'num_chq')
    def _compute_card(self):
        for rec in self:
            rec.summary_card = f"""
            <div style="padding:12px; border-radius:12px; background:#fafafa;
                        border:1px solid #ddd; width:100%; margin-top:10px;">
                <h3 style="margin:0; font-size:16px;">📄 Talon : {rec.name_shown}</h3>
                <p style="margin:4px 0;">Total : <b>{rec.num_chq}</b></p>
                <p style="margin:4px 0; color:#dc3545;">
                    🔴 Utilisés : <b>{rec.used_chqs}</b>
                </p>
                <p style="margin:4px 0; color:#28a745;">
                    🟢 Restants : <b>{rec.unused_chqs}</b>
                </p>
                <p style="margin:4px 0; color:#17a2b8;">
                    📊 Pourcentage : <b>{round(rec.usage_percentage, 2)}%</b>
                </p>
            </div>
            """

    # -------------------------------------------------------------------
    # Barre de progression dynamique
    # -------------------------------------------------------------------
    @api.depends('used_chqs', 'num_chq')
    def _compute_progress(self):
        for rec in self:

            if rec.num_chq:
                pct = int((rec.used_chqs / rec.num_chq) * 100)
            else:
                pct = 0

            # Couleur dynamique
            if pct < 50:
                color = "#28a745"  # vert
            elif pct < 80:
                color = "#fd7e14"  # orange
            else:
                color = "#dc3545"  # rouge

            rec.progress_html = f"""
                <div style="width:100%; background:#e9ecef; border-radius:8px; height:18px;">
                    <div style="width:{pct}%; background:{color}; height:18px; border-radius:8px;"></div>
                </div>
                <div style="font-size:12px; text-align:center; margin-top:3px; font-weight:600;">
                    {pct}% utilisé
                </div>
            """

    # -------------------------------------------------------------------
    # Calcul des chèques utilisés/restants + Pourcentage (Stored)
    # -------------------------------------------------------------------
    @api.depends('used_chqs', 'num_chq')
    def _compute_usage_percentage(self):
        for rec in self:
            if rec.num_chq:
                rec.usage_percentage = (rec.used_chqs / rec.num_chq) * 100
            else:
                rec.usage_percentage = 0.0

    @api.depends('cheque_ids', 'num_chq')
    def _compute_counts(self):
        for rec in self:
            rec.used_chqs = len(rec.cheque_ids)
            rec.unused_chqs = rec.num_chq - rec.used_chqs
