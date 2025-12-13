from odoo import models, fields, api

class FinanceTalon(models.Model):
    _name = 'finance.talon'
    _description = 'Talons'
    _rec_name = 'name_shown'

    name = fields.Char(string='Talon', required=True, size=7)
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
    missing_cheques_html = fields.Html(
        string="Chèques absents",
        compute="_compute_missing_cheques_html",
        sanitize=False
    )
    missing_chqs = fields.Integer(
        string="Chèques absents",
        compute="_compute_missing_chqs"
    )

    # -------------------------------------------------------------------
    # Bouton vers chqs du talon
    # -------------------------------------------------------------------
    def action_open_cheques(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chèques du talon',
            'res_model': 'datacheque',
            'view_mode': 'tree,form',
            'domain': [('talon_id', '=', self.id)],
            'context': {
                'default_talon_id': self.id,
            }
        }

    # -------------------------------------------------------------------
    # Résumé stylé (carte HTML moderne - centrée)
    # -------------------------------------------------------------------
    @api.depends('used_chqs', 'unused_chqs', 'num_chq')
    def _compute_card(self):
        for rec in self:
            rec.summary_card = f"""
            <div style="display: flex; justify-content: flex-start; width: 100%; margin-top: 10px;">
                <div style="
                    max-width: 450px;
                    width: 100%;
                    padding: 20px;
                    border-radius: 16px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.25);
                    color: white;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                ">
                    <div style="display: flex; align-items: center; margin-bottom: 16px;">
                        <div style="
                            width: 48px;
                            height: 48px;
                            background: rgba(255,255,255,0.2);
                            border-radius: 12px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 24px;
                            margin-right: 12px;
                        ">📄</div>
                        <h3 style="margin: 0; font-size: 20px; font-weight: 600;">
                            {rec.name_shown}
                        </h3>
                    </div>
                    
                    <div style="
                        display: grid;
                        grid-template-columns: repeat(2, 1fr);
                        gap: 12px;
                        margin-top: 16px;
                    ">
                        <div style="
                            background: rgba(255,255,255,0.15);
                            backdrop-filter: blur(10px);
                            padding: 12px;
                            border-radius: 12px;
                            border: 1px solid rgba(255,255,255,0.2);
                        ">
                            <div style="font-size: 12px; opacity: 0.9; margin-bottom: 4px;">
                                Total
                            </div>
                            <div style="font-size: 24px; font-weight: 700;">
                                {rec.num_chq}
                            </div>
                        </div>
                        
                        <div style="
                            background: rgba(255,255,255,0.15);
                            backdrop-filter: blur(10px);
                            padding: 12px;
                            border-radius: 12px;
                            border: 1px solid rgba(255,255,255,0.2);
                        ">
                            <div style="font-size: 12px; opacity: 0.9; margin-bottom: 4px;">
                                📊 Utilisation
                            </div>
                            <div style="font-size: 24px; font-weight: 700;">
                                {round(rec.usage_percentage, 1)}%
                            </div>
                        </div>
                        
                        <div style="
                            background: rgba(220, 53, 69, 0.3);
                            backdrop-filter: blur(10px);
                            padding: 12px;
                            border-radius: 12px;
                            border: 1px solid rgba(220, 53, 69, 0.4);
                        ">
                            <div style="font-size: 12px; opacity: 0.9; margin-bottom: 4px;">
                                🔴 Utilisés
                            </div>
                            <div style="font-size: 24px; font-weight: 700;">
                                {rec.used_chqs}
                            </div>
                        </div>
                        
                        <div style="
                            background: rgba(40, 167, 69, 0.3);
                            backdrop-filter: blur(10px);
                            padding: 12px;
                            border-radius: 12px;
                            border: 1px solid rgba(40, 167, 69, 0.4);
                        ">
                            <div style="font-size: 12px; opacity: 0.9; margin-bottom: 4px;">
                                🟢 Restants
                            </div>
                            <div style="font-size: 24px; font-weight: 700;">
                                {rec.unused_chqs}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """

    # -------------------------------------------------------------------
    # Barre de progression moderne avec animation
    # -------------------------------------------------------------------
    @api.depends('used_chqs', 'num_chq')
    def _compute_progress(self):
        for rec in self:
            if rec.num_chq:
                pct = int((rec.used_chqs / rec.num_chq) * 100)
            else:
                pct = 0

            # Couleurs et emojis dynamiques
            if pct < 50:
                color = "#28a745"
                gradient = "linear-gradient(90deg, #28a745 0%, #20c997 100%)"
                emoji = "🟢"
                status = "Excellent"
            elif pct < 80:
                color = "#fd7e14"
                gradient = "linear-gradient(90deg, #fd7e14 0%, #ffc107 100%)"
                emoji = "🟡"
                status = "Attention"
            else:
                color = "#dc3545"
                gradient = "linear-gradient(90deg, #dc3545 0%, #e83e8c 100%)"
                emoji = "🔴"
                status = "Critique"

            rec.progress_html = f"""
                <div style="
                    padding: 16px;
                    background: #f8f9fa;
                    border-radius: 12px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                ">
                    <div style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 8px;
                    ">
                        <span style="font-size: 13px; color: #6c757d; font-weight: 600;">
                            {emoji} {status}
                        </span>
                        <span style="
                            font-size: 20px;
                            font-weight: 700;
                            color: {color};
                        ">
                            {pct}%
                        </span>
                    </div>
                    
                    <div style="
                        width: 100%;
                        height: 24px;
                        background: #e9ecef;
                        border-radius: 12px;
                        overflow: hidden;
                        box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
                    ">
                        <div style="
                            width: {pct}%;
                            height: 100%;
                            background: {gradient};
                            border-radius: 12px;
                            box-shadow: 0 2px 8px rgba({color}, 0.4);
                            transition: width 0.3s ease;
                            display: flex;
                            align-items: center;
                            justify-content: flex-end;
                            padding-right: 8px;
                        ">
                            <span style="
                                color: white;
                                font-size: 11px;
                                font-weight: 700;
                                text-shadow: 0 1px 2px rgba(0,0,0,0.2);
                            ">
                                {rec.used_chqs}/{rec.num_chq}
                            </span>
                        </div>
                    </div>
                </div>
            """

    # -------------------------------------------------------------------
    # Déterminer le nombre des chqs absents
    # -------------------------------------------------------------------
    @api.depends('cheque_ids.chq', 'name')
    def _compute_missing_chqs(self):
        for talon in self:
            # sécurité
            if not talon.name or not talon.name.strip().isdigit():
                talon.missing_chqs = 0
                continue

            talon_start = int(talon.name.strip())

            # récupérer les chèques numériques existants
            chqs = [
                int(c.chq) for c in talon.cheque_ids
                if c.chq and c.chq.strip().isdigit()
            ]

            if not chqs:
                talon.missing_chqs = 0
                continue

            max_chq = max(chqs)
            used = len(chqs)

            missing = (max_chq - talon_start + 1) - used
            talon.missing_chqs = max(missing, 0)

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

    @api.depends('cheque_ids.chq', 'num_chq', 'name', 'ste_id')
    def _compute_missing_cheques_html(self):
        for talon in self:
            # --- Validation robuste du talon ---
            raw_name = (talon.name or "").strip()

            try:
                start = int(raw_name)
            except (ValueError, TypeError):
                talon.missing_cheques_html = """
                    <div style="
                        padding: 16px;
                        background: #fff3cd;
                        border-left: 4px solid #ffc107;
                        border-radius: 8px;
                        color: #856404;
                    ">
                        <strong>⚠️ Attention</strong><br/>
                        Données du talon invalides (numéro non numérique)
                    </div>
                """
                continue

            if not talon.num_chq or talon.num_chq <= 0:
                talon.missing_cheques_html = """
                    <div style="
                        padding: 16px;
                        background: #fff3cd;
                        border-left: 4px solid #ffc107;
                        border-radius: 8px;
                        color: #856404;
                    ">
                        <strong>⚠️ Attention</strong><br/>
                        Données du talon invalides (nombre de chèques)
                    </div>
                """
                continue

            # --- Numéros de chèques existants ---
            existing_numbers = set()
            for chq in talon.cheque_ids:
                raw_chq = (chq.chq or "").strip()
                try:
                    existing_numbers.add(int(raw_chq))
                except (ValueError, TypeError):
                    continue

            # 👉 S’il n’y a encore aucun chèque saisi, on n’affiche rien
            if not existing_numbers:
                talon.missing_cheques_html = """
                    <div style="padding: 16px; color: #6c757d; font-style: italic;">
                        ℹ️ Aucun chèque encore saisi pour ce talon
                    </div>
                """
                continue

            # --- Nouvelle borne de fin = plus grand chèque saisi ---
            end = max(existing_numbers)

            # --- Numéros de chèques existants ---
            existing_numbers = set()
            for chq in talon.cheque_ids:
                raw_chq = (chq.chq or "").strip()
                try:
                    existing_numbers.add(int(raw_chq))
                except (ValueError, TypeError):
                    continue

            # --- Calcul des chèques absents ---
            missing = [
                num for num in range(start, end + 1)
                if num not in existing_numbers
            ]

            # --- Aucun chèque manquant ---
            if not missing:
                talon.missing_cheques_html = """
                    <div style="
                        padding: 20px;
                        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
                        border-radius: 12px;
                        border: 2px solid #28a745;
                        text-align: center;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    ">
                        <div style="font-size: 48px; margin-bottom: 8px;">✅</div>
                        <div style="
                            font-size: 18px;
                            font-weight: 700;
                            color: #155724;
                            margin-bottom: 4px;
                        ">
                            Parfait !
                        </div>
                        <div style="color: #155724; font-size: 14px;">
                            Tous les chèques de ce talon sont présents
                        </div>
                    </div>
                """
                continue

            # --- Construction HTML moderne pour les chèques manquants ---
            lines = []
            for idx, num in enumerate(missing):
                lines.append(f"""
                    <div style="
                        padding: 14px;
                        background: white;
                        border-radius: 10px;
                        margin-bottom: 8px;
                        border-left: 4px solid #dc3545;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                        transition: transform 0.2s, box-shadow 0.2s;
                    ">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <div>
                                <div style="
                                    display: inline-block;
                                    background: #dc3545;
                                    color: white;
                                    padding: 4px 10px;
                                    border-radius: 6px;
                                    font-weight: 700;
                                    font-size: 14px;
                                    margin-bottom: 6px;
                                ">
                                    CHQ {str(num).zfill(7)}
                                </div>
                                <div style="font-size: 12px; color: #6c757d;">
                                    <span style="font-weight: 600;">Société:</span> {talon.ste_id.name}
                                    <span style="margin: 0 8px;">•</span>
                                    <span style="font-weight: 600;">Talon:</span> {talon.name_shown}
                                </div>
                            </div>
                            <div style="
                                width: 32px;
                                height: 32px;
                                background: rgba(220, 53, 69, 0.1);
                                border-radius: 50%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-size: 18px;
                            ">
                                ⚠️
                            </div>
                        </div>
                    </div>
                """)

            talon.missing_cheques_html = f"""
                <div style="
                    padding: 16px;
                    background: #f8f9fa;
                    border-radius: 12px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                ">
                    <div style="
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        padding: 12px 16px;
                        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
                        border-radius: 10px;
                        margin-bottom: 16px;
                        border: 2px solid #dc3545;
                    ">
                        <div>
                            <div style="font-size: 16px; font-weight: 700; color: #721c24;">
                                🔴 Chèques absents
                            </div>
                            <div style="font-size: 13px; color: #721c24; margin-top: 2px;">
                                {len(missing)} chèque{'s' if len(missing) > 1 else ''} manquant{'s' if len(missing) > 1 else ''}
                            </div>
                        </div>
                        <div style="
                            background: #dc3545;
                            color: white;
                            padding: 6px 14px;
                            border-radius: 20px;
                            font-weight: 700;
                            font-size: 18px;
                        ">
                            {len(missing)}
                        </div>
                    </div>
                    
                    <div style="max-height: 500px; overflow-y: auto;">
                        {''.join(lines)}
                    </div>
                </div>
            """