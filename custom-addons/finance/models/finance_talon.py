from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

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
    ], string='Etat', compute="_compute_etat", store=True, readonly=True)

    used_chqs = fields.Integer(string='Nombre de chqs utilisés', compute='_compute_counts', store=True)
    unused_chqs = fields.Integer(string='Nombre de chqs restants', compute='_compute_counts', store=True)
    usage_percentage = fields.Float(string='% Utilisation', compute='_compute_usage_percentage', store=True)
    
    cheque_ids = fields.One2many('datacheque', 'talon_id', string='Chèques')
    effet_ids = fields.One2many('finance.effet', 'talon_id', string='Effets')

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
    last_used_chq = fields.Char(
        string="Dernier chèque utilisé",
        compute="_compute_last_used_chq",
        store=True
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
    # Détermination de l'état
    # -------------------------------------------------------------------
    @api.depends('used_chqs', 'num_chq')
    def _compute_etat(self):
        for rec in self:
            # sécurité
            if not rec.num_chq or rec.num_chq <= 0:
                rec.etat = False
                continue

            if rec.used_chqs == 0:
                rec.etat = 'coffre'
            elif rec.used_chqs >= rec.num_chq:
                rec.etat = 'cloture'
            else:
                rec.etat = 'actif'

    @api.depends('cheque_ids.chq', 'effet_ids.serie')
    def _compute_last_used_chq(self):
        for rec in self:
            numeric_chqs = []
            for chq in rec.cheque_ids:
                raw = (chq.chq or "").strip()
                if raw.isdigit():
                    numeric_chqs.append(int(raw))
            for effet in rec.effet_ids:
                raw = (effet.serie or "").strip()
                if raw.isdigit():
                    numeric_chqs.append(int(raw))

            if numeric_chqs:
                rec.last_used_chq = str(max(numeric_chqs)).zfill(7)
            else:
                rec.last_used_chq = False

    # -------------------------------------------------------------------
    # Résumé stylé (carte HTML moderne - centrée)
    # -------------------------------------------------------------------
    @api.depends('used_chqs', 'unused_chqs', 'num_chq', 'last_used_chq')
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

                    <div style="
                        margin-top: 12px;
                        background: rgba(255, 255, 255, 0.15);
                        backdrop-filter: blur(10px);
                        border-radius: 12px;
                        padding: 12px 16px;
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                    ">
                        <div style="font-size: 13px; font-weight: 600; opacity: 0.9;">
                             🏷️ Dernier chèque utilisé
                        </div>
                        <div style="font-size: 16px; font-weight: 700; letter-spacing: 0.5px;">
                             {rec.last_used_chq if rec.last_used_chq else "Aucun chèque utilisé"}
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
                # > 80% usage: Check if a next numeric talon exists
                next_talon_name = None
                
                # Only check if current name is numeric
                current_name_raw = (rec.name or "").strip()
                if current_name_raw.isdigit() and rec.ste_id:
                    current_val = int(current_name_raw)
                    
                    # Find all talons for the same company
                    company_talons = self.search([('ste_id', '=', rec.ste_id.id)])
                    
                    # Store (integer_value, original_name) tuples
                    numeric_talons = []
                    for t in company_talons:
                        t_name_raw = (t.name or "").strip()
                        if t_name_raw.isdigit():
                            numeric_talons.append((int(t_name_raw), t.name_shown))
                    
                    # Sort numerically
                    numeric_talons.sort(key=lambda x: x[0])
                    
                    # Find current position and check next
                    # We iterate to find the exact match for current_val
                    # Then look if there is an element at index + 1
                    for idx, (val, name_shown) in enumerate(numeric_talons):
                        if val == current_val:
                            # If there is a next element
                            if idx + 1 < len(numeric_talons):
                                next_talon_name = numeric_talons[idx+1][1] # Get name_shown of next
                            break

                if next_talon_name:
                    # Next talon exists -> Warning (Orange)
                    color = "#fd7e14"
                    gradient = "linear-gradient(90deg, #fd7e14 0%, #ffc107 100%)"
                    emoji = "🟡"
                    status = f"Attention – ouvrir talon {next_talon_name}"
                else:
                    # No next talon -> Critical (Red)
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
    @api.depends('cheque_ids.chq', 'name', 'effet_ids.serie')
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
            effets = [
                int(e.serie) for e in talon.effet_ids
                if e.serie and e.serie.strip().isdigit()
            ]

            all_used = chqs + effets
            if not all_used:
                talon.missing_chqs = 0
                continue

            max_chq = max(all_used)
            used = len(set(all_used))

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

    @api.depends('cheque_ids', 'effet_ids', 'num_chq')
    def _compute_counts(self):
        for rec in self:
            # Count unique check numbers
            unique_chqs = {c.chq for c in rec.cheque_ids if c.chq}
            unique_effets = {e.serie for e in rec.effet_ids if e.serie}
            rec.used_chqs = len(unique_chqs.union(unique_effets))
            rec.unused_chqs = rec.num_chq - rec.used_chqs

    # -------------------------------------------------------------------
    # Helper: Get missing cheques numbers
    # -------------------------------------------------------------------
    def _get_missing_cheques_numbers(self):
        self.ensure_one()
        # --- Validation robuste du talon ---
        raw_name = (self.name or "").strip()

        try:
            start = int(raw_name)
        except (ValueError, TypeError):
            return []

        if not self.num_chq or self.num_chq <= 0:
            return []

        # --- Numéros de chèques existants ---
        existing_numbers = set()
        for chq in self.cheque_ids:
            raw_chq = (chq.chq or "").strip()
            try:
                existing_numbers.add(int(raw_chq))
            except (ValueError, TypeError):
                continue
        for effet in self.effet_ids:
            raw_serie = (effet.serie or "").strip()
            try:
                existing_numbers.add(int(raw_serie))
            except (ValueError, TypeError):
                continue

        # 👉 S’il n’y a encore aucun chèque saisi, on n’affiche rien
        if not existing_numbers:
            return []

        # --- Nouvelle borne de fin = plus grand chèque saisi ---
        end = max(existing_numbers)

        # --- Calcul des chèques absents ---
        missing = [
            num for num in range(start, end + 1)
            if num not in existing_numbers
        ]
        return missing

    @api.depends('cheque_ids.chq', 'effet_ids.serie', 'num_chq', 'name', 'ste_id')
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
            
            # --- Check if any cheques exist (simple check to avoid loading logic if empty) ---
            if not talon.cheque_ids and not talon.effet_ids:
                 talon.missing_cheques_html = """
                    <div style="padding: 16px; color: #6c757d; font-style: italic;">
                        ℹ️ Aucun chèque/effet encore saisi pour ce talon
                    </div>
                """
                 continue

            # --- Use Helper ---
            missing = talon._get_missing_cheques_numbers()
            
            # If helper returns empty, check why (validation handled above, so maybe no cheques valid?)
            # Re-check existing numbers strictly for the "None info" message
            existing_count = 0 
            for c in talon.cheque_ids: 
                if c.chq and c.chq.strip().isdigit(): existing_count += 1
            for e in talon.effet_ids:
                if e.serie and e.serie.strip().isdigit(): existing_count += 1
            
            if existing_count == 0:
                 talon.missing_cheques_html = """
                    <div style="padding: 16px; color: #6c757d; font-style: italic;">
                        ℹ️ Aucun chèque/effet encore saisi pour ce talon
                    </div>
                """
                 continue

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
                                # border-radius: 50%;
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

    def action_export_missing_cheques_excel(self):
        self.ensure_one()
        if not xlsxwriter:
            raise UserError("La librairie 'xlsxwriter' n'est pas installée.")

        missing_list = self._get_missing_cheques_numbers()
        if not missing_list:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Aucun chèque manquant",
                    "message": "Bravo ! Tous les chèques sont présents, aucun fichier à générer.",
                    "type": "success",
                    "sticky": False,
                },
            }

        # --- Generate Excel ---
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Chèques Manquants")

        # Styles
        style_header = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#f2f2f2', 'border': 1})
        style_cell = workbook.add_format({'align': 'center', 'border': 1})

        # Headers
        headers = ["Société", "Talon", "N° Chèque Manquant"]
        sheet.set_column(0, 0, 25)  # Société
        sheet.set_column(1, 1, 20)  # Talon
        sheet.set_column(2, 2, 20)  # N° Chèque

        sheet.write_row(0, 0, headers, style_header)

        # Content
        row = 1
        for num in missing_list:
            sheet.write(row, 0, self.ste_id.name or "", style_cell)
            sheet.write(row, 1, self.name_shown or "", style_cell)
            sheet.write(row, 2, str(num).zfill(7), style_cell)
            row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        # Create attachment
        sanitized_talon = "".join([c for c in (self.name_shown or "") if c.isalnum() or c in (' ', '-', '_')]).strip()
        filename = f"Manquants_{self.ste_id.name}_{sanitized_talon}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': file_data,
            'type': 'binary',
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def get_talon_stats(self):
        self.ensure_one()
        return {
            'total': self.num_chq,
            'used': self.used_chqs,
            'remaining': self.unused_chqs,
            'percentage': round(self.usage_percentage, 1),
            'etat': dict(self._fields['etat'].selection).get(self.etat, self.etat)
        }

    def get_outgoing_checks_data(self):
        self.ensure_one()
        data = []
        # Checks
        for c in self.cheque_ids:
            data.append({
                'ref': c.chq,
                'benif': c.benif_id.name if c.benif_id else "",
                'date': c.date_emission,
                'amount': c.amount,
                'status': 'Encaissé' if c.encours == 'encaisse' else 'En cours',
                'date_encaissement': c.date_encaissement,
                'type': 'Chèque'
            })
        # Effects
        for e in self.effet_ids:
            data.append({
                'ref': e.serie,
                'benif': e.benif_id.name if e.benif_id else "",
                'date': e.date_emission,
                'amount': e.montant,
                'status': 'Encaissé' if e.state == 'encaisse' else 'En cours',
                'date_encaissement': e.date_encaissement,
                'type': 'Effet'
            })
        # Sort by ref (numeric if possible)
        try:
            data.sort(key=lambda x: int(x['ref']) if (x['ref'] and x['ref'].isdigit()) else 0)
        except:
            pass
        return data