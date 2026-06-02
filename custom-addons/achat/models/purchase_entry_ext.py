from odoo import models, fields, api
from odoo.exceptions import ValidationError
from markupsafe import Markup
from datetime import date, timedelta
import base64
import io
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class LogisticsEntry(models.Model):
    _inherit = 'logistique.entry'

    contract_id = fields.Many2one('achat.contract', string='Contract', domain="[('state', '=', 'open')]", required=False)
    free_time_negotiated = fields.Integer(string='Negotiated Free Time')

    is_non_change = fields.Boolean(string='Non Changé', default=False,
                                   help='Cocher si le dossier n\'a pas encore été changé')

    is_faux = fields.Boolean(
        string='Faux',
        default=False,
        tracking=True,
        help="Coché automatiquement par l'IA si l'Invoice ne correspond pas aux données. L'admin peut le décocher manuellement."
    )

    ai_status = fields.Selection([
        ('unverified', 'Non vérifié'),
        ('validated', 'Validé'),
        ('error', 'Erreur')
    ], string='Statut IA', default='unverified', tracking=True)

    is_onicl_applicable = fields.Boolean(
        string='Applicable ONICL',
        compute='_compute_is_onicl_applicable',
        search='_search_is_onicl_applicable'
    )
    
    onicl_days_to_eta = fields.Integer(
        string='Jours restants (ETA)',
        compute='_compute_onicl_days_to_eta',
        help="Nombre de jours restants jusqu'à l'ETA"
    )

    onicl_state = fields.Selection([
        ('new', 'Nouveau'),
        ('ricpc_sent', 'Demande RCPSS envoyée'),
        ('ricpc_error', 'Erreur RCPSS'),
        ('ricpc_approved', 'Approuvé RCPSS'),
        ('onicl_entered', 'Saisi sur système ONICL'),
        ('validated', 'Validé'),
        ('confirmed', 'Confirmé'),
        ('portnet_validated', 'Validé sur Portnet'),
    ], string='Statut ONICL', default='new', tracking=True)

    onicl_pdf = fields.Binary(string='Capture mise à disposition', attachment=True)
    onicl_pdf_name = fields.Char(string='Nom de la Capture mise à disposition')

    recepisse_pdf = fields.Binary(string='Récépissé', attachment=True)
    recepisse_pdf_name = fields.Char(string='Nom du Récépissé')

    def action_onicl_send_ricpc(self):
        for rec in self:
            rec.onicl_state = 'ricpc_sent'

    def action_onicl_set_error(self):
        for rec in self:
            rec.onicl_state = 'ricpc_error'

    def action_onicl_approve(self):
        for rec in self:
            rec.onicl_state = 'ricpc_approved'

    def action_onicl_enter(self):
        for rec in self:
            rec.onicl_state = 'onicl_entered'

    def action_onicl_validate(self):
        for rec in self:
            rec.onicl_state = 'validated'

    def action_onicl_confirm(self):
        for rec in self:
            if not rec.onicl_pdf or not rec.recepisse_pdf:
                raise ValidationError("Vous devez importer la Capture mise à disposition et le Récépissé avant de confirmer ce dossier.")
            rec.onicl_state = 'confirmed'

    def action_onicl_validate_portnet(self):
        for rec in self:
            rec.onicl_state = 'portnet_validated'

    @api.depends('eta', 'achat_article_id.is_onicl')
    def _compute_is_onicl_applicable(self):
        today = date.today()
        fifteen_days_later = today + timedelta(days=15)
        for rec in self:
            is_onicl = rec.achat_article_id.is_onicl if rec.achat_article_id else False
            rec.is_onicl_applicable = is_onicl and bool(rec.eta) and rec.eta <= fifteen_days_later

    def _search_is_onicl_applicable(self, operator, value):
        if operator not in ('=', '!='):
            raise NotImplementedError("Only '=' and '!=' operators are supported")
        today = date.today()
        fifteen_days_later = today + timedelta(days=15)
        
        onicl_articles = self.env['achat.article'].search([('is_onicl', '=', True)])
        onicl_article_ids = onicl_articles.ids
        
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [
                ('achat_article_id', 'in', onicl_article_ids),
                ('eta', '!=', False),
                ('eta', '<=', fifteen_days_later)
            ]
        else:
            return ['|', '|',
                ('achat_article_id', 'not in', onicl_article_ids),
                ('eta', '=', False),
                ('eta', '>', fifteen_days_later)
            ]

    @api.depends('eta')
    def _compute_onicl_days_to_eta(self):
        today = date.today()
        for rec in self:
            if rec.eta:
                delta = rec.eta - today
                rec.onicl_days_to_eta = delta.days
            else:
                rec.onicl_days_to_eta = 0

    date_booking = fields.Date(string='Date of Booking')
    date_docs_received = fields.Date(string='Date Documents Received')
    date_docs_confirmed = fields.Date(string='Date Documents Confirmed')

    origin_id = fields.Many2one(
        'achat.origin',
        string='Origin'
    )

    
    # Document Link
    document_ids = fields.One2many('logistique.entry.document', 'entry_id', string='Documents')

    display_name = fields.Char(compute='_compute_display_name') # Just to ensure we have it if needed

    eta_this_week = fields.Boolean(
        string='ETA cette semaine',
        compute='_compute_eta_this_week',
        store=True,
        help='True if ETA <= next Thursday (inclusive) and port_status is on_port',
    )

    @api.depends('eta', 'port_status')
    def _compute_eta_this_week(self):
        today = date.today()
        days_to_thursday = (3 - today.weekday()) % 7
        next_thursday = today + timedelta(days=days_to_thursday)
        for rec in self:
            rec.eta_this_week = (
                rec.port_status == 'on_port'
                and bool(rec.eta)
                and rec.eta <= next_thursday
            )

    calendar_label = fields.Char(string='Label Calendrier', compute='_compute_calendar_label')

    @api.depends('supplier_id.name', 'achat_article_id.name', 'ste_id.name', 'amount_total')
    def _compute_calendar_label(self):
        for rec in self:
            supplier = rec.supplier_id.name or ''
            article = rec.achat_article_id.name or ''
            ste = rec.ste_id.name or ''
            total = rec.amount_total or 0.0
            # Format total with space as thousands separator
            total_str = "{:,.2f}".format(total).replace(",", " ")
            rec.calendar_label = f"{supplier} - {article} - {ste} - {total_str} USD"

    @api.depends('calendar_label', 'bl_number')
    def _compute_display_name(self):
        for rec in self:
            if self.env.context.get('show_bl_number'):
                rec.display_name = rec.bl_number or "Nouveau"
            elif rec.calendar_label:
                rec.display_name = rec.calendar_label
            else:
                rec.display_name = rec.bl_number or "Nouveau"

    @api.constrains('bl_number', 'contract_id')
    def _check_bl_contract_unique(self):
        """Prevent duplicate BL numbers for the same contract"""
        for rec in self:
            if rec.bl_number and rec.contract_id:
                duplicate = self.search([
                    ('id', '!=', rec.id),
                    ('bl_number', '=', rec.bl_number),
                    ('contract_id', '=', rec.contract_id.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f"The BL '{rec.bl_number}' exists already for this contract '{rec.contract_id.name}'.\n"
                        f"The same BL number cannot be used twice for the same contract."
                    )

    @api.constrains('price_unit')
    def _check_price_unit(self):
        for rec in self:
            if rec.price_unit <= 0:
                raise ValidationError("Le prix unitaire (P.U) doit être strictement supérieur à 0.")

    @api.constrains('invoice_number', 'ste_id')
    def _check_invoice_ste_achat(self):
        for rec in self:
            if not rec.invoice_number:
                continue
            # Search for other entries with the same invoice
            domain = [('invoice_number', '=', rec.invoice_number), ('id', '!=', rec.id)]
            other_entries = self.search(domain)
            for other in other_entries:
                if other.ste_id != rec.ste_id:
                    raise ValidationError(
                        "L'invoice \"%s\" est déjà utilisé par une autre société (%s) dans un autre dossier!"
                        % (rec.invoice_number, other.ste_id.name)
                    )

    def action_confirm_purchase(self):
        if not self.env.user.has_group('achat.group_purchase_manager'):
            raise ValidationError("Seul un Manager peut confirmer un dossier.")
        self.write({'purchase_state': 'confirmed'})

    def action_reset_to_initial(self):
        """Admin-only: Reset purchase state back to Initial."""
        self.write({'purchase_state': 'initial'})

    def action_reset_to_draft(self):
        """Admin-only: Reset purchase state back to Draft."""
        self.write({'purchase_state': 'draft'})

    def action_verify_invoice_ai(self):
        """Verify invoices using AI for selected dossiers."""
        api_key = self.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not api_key:
            raise ValidationError("La clé API OpenAI n'est pas configurée dans les Paramètres Système sous 'whatsapp_stock.openai_key'.")

        import base64
        import requests
        import json

        for rec in self:
            invoice_doc = rec.env['logistique.entry.document'].search([
                ('entry_id', '=', rec.id),
                ('document_type', '=', 'invoice')
            ], limit=1)

            if not invoice_doc or not invoice_doc.file:
                rec.message_post(body=Markup("<b>Saut de la vérification IA</b> : Aucun document de type 'Invoice' (Commercial Invoice) n'est attaché à ce dossier."))
                continue

            try:
                # Le fichier est déjà en base64 dans Odoo, on le passe directement
                pdf_bytes = invoice_doc.file
                pdf_b64 = pdf_bytes.decode('utf-8') if isinstance(pdf_bytes, bytes) else pdf_bytes

                data_to_verify = {
                    "contract_num": rec.contract_num or "",
                    "invoice_number": rec.invoice_number or "",
                    "lot": rec.lot or "",
                    "weight_tonnes": rec.weight or 0.0,
                    "total_cfr_usd": rec.amount_total or 0.0,
                    "origin": rec.origin_id.name if rec.origin_id else ""
                }

                # Construire la liste des champs NON-vides à vérifier
                fields_to_check = []
                if data_to_verify["contract_num"]:
                    fields_to_check.append(f"- Contract : '{data_to_verify['contract_num']}'")
                if data_to_verify["invoice_number"]:
                    fields_to_check.append(f"- Invoice No. : '{data_to_verify['invoice_number']}'")
                if data_to_verify["lot"]:
                    fields_to_check.append(f"- Lot No. : '{data_to_verify['lot']}'")
                if data_to_verify["weight_tonnes"]:
                    fields_to_check.append(f"- Poids : {data_to_verify['weight_tonnes']} tonnes (peut apparaître comme MT, T, ou en KG × 1000)")
                if data_to_verify["total_cfr_usd"]:
                    fields_to_check.append(f"- Montant Total (CFR) : {data_to_verify['total_cfr_usd']} USD")
                if data_to_verify["origin"]:
                    fields_to_check.append(f"- Origine : '{data_to_verify['origin']}'")

                if not fields_to_check:
                    rec.message_post(body=Markup("<b>Saut de la vérification IA</b> : Aucun champ renseigné à vérifier (contract, invoice, lot, poids, total CFR, origine)."))
                    continue

                fields_str = "\n".join(fields_to_check)

                prompt_text = f"""Vous êtes un agent de contrôle logistique. Lisez attentivement le document commercial joint (invoice PDF).

Voici les informations saisies dans le système pour CETTE facture. Vérifiez UNIQUEMENT les champs listés ci-dessous (les autres sont vides et doivent être ignorés) :

{fields_str}

RÈGLES DE COMPARAISON STRICTES :
1. TEXTE (contract, invoice, lot, origin) : Comparez sans tenir compte de la casse et en ignorant les espaces, tirets (-), points (.), slashes (/).
   - ⚠️ RÈGLE DE CORRESPONDANCE LOGIQUE : Considérez que c'est une CORRESPONDANCE si le numéro Odoo est la partie principale du numéro PDF.
   - Ignorez les ZÉROS INUTILES au début et les préfixes/suffixes.
   - Exemple : Odoo="152" match avec PDF="A26/202600152" (car 152 est le coeur du numéro).
   - Exemple : Odoo="358" match avec PDF="358/2026".
   - 🚫 RÈGLE ABSOLUE : Si les valeurs Odoo et PDF sont identiques (ex: 35853 et 35853), c'est une correspondance PARFAITE. Ne les ajoutez JAMAIS dans 'mismatches'.
2. POIDS : Le poids en Odoo est en TONNES. Valeurs équivalentes : 44 tonnes = 44 MT = 44 T = 44,000 KG = 44.000 KG.
3. MONTANT TOTAL (CFR) : Comparaison stricte sur le nombre total de la facture (souvent marqué comme 'Total Amount', 'CFR Value', 'Balance', 'Total CFR', etc.). "80300" = "80,300" = "80.300" = "US$80,300.00".
4. BÉNÉFICE DU DOUTE : Soyez très tolérant. Ne mettez is_faux=true que si les chiffres sont totalement différents et sans aucun lien logique.
5. CHAMPS ABSENTS DU PDF : Si un champ n'apparaît pas clairement dans le document, ignorez-le.

Répondez UNIQUEMENT avec du JSON valide, sans explication, sans markdown :
{{
    "is_faux": true,
    "mismatches": [
        {{"field": "Nom du champ concerné", "odoo_value": "valeur Odoo", "pdf_value": "valeur trouvée dans le PDF"}}
    ],
    "reason": "Résumé en français des incompatibilités trouvées."
}}
OU si tout est correct :
{{
    "is_faux": false,
    "mismatches": [],
    "reason": ""
}}"""

                # Utilisation de l'API Responses OpenAI qui supporte les PDFs nativement
                payload = {
                    "model": "gpt-4o",
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_file",
                                    "filename": invoice_doc.file_name or "invoice.pdf",
                                    "file_data": f"data:application/pdf;base64,{pdf_b64}"
                                },
                                {
                                    "type": "input_text",
                                    "text": prompt_text
                                }
                            ]
                        }
                    ],
                    "text": {
                        "format": {
                            "type": "json_object"
                        }
                    },
                    "temperature": 0.0,
                    "max_output_tokens": 800
                }

                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }

                resp = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=120)
                resp.raise_for_status()
                ai_data = resp.json()
                
                raw_content = ""
                for output_item in ai_data.get("output", []):
                    for content_item in output_item.get("content", []):
                        if content_item.get("type") == "output_text":
                            raw_content = content_item.get("text", "")
                            break

                if not raw_content:
                    rec.message_post(body=Markup("<b>Erreur IA</b> : OpenAI n'a retourné aucune réponse pour ce document."))
                    continue

                result = json.loads(raw_content)
                is_faux_val = result.get("is_faux", False)
                reason = result.get("reason", "")
                mismatches = result.get("mismatches", [])

                rec.sudo().write({
                    'is_faux': is_faux_val,
                    'ai_status': 'error' if is_faux_val else 'validated'
                })

                if is_faux_val:
                    details = Markup("")
                    if mismatches:
                        items = Markup("").join(
                            Markup(
                                "<li><b>{field}</b> : "
                                "Odoo = <code style='background:#ffeaea;padding:2px 5px;border-radius:3px;'>{odoo}</code> "
                                "&nbsp;➡&nbsp; "
                                "PDF = <code style='background:#fff3cd;padding:2px 5px;border-radius:3px;'>{pdf}</code></li>"
                            ).format(
                                field=m.get('field', ''),
                                odoo=m.get('odoo_value', ''),
                                pdf=m.get('pdf_value', '')
                            )
                            for m in mismatches
                        )
                        details = Markup("<ul style='margin:8px 0 8px 16px;'>{}</ul>").format(items)

                    rec.message_post(body=Markup(
                        "<div style='border-left:4px solid #dc3545;padding:8px 12px;background:#fff5f5;border-radius:4px;'>"
                        "<span style='color:#dc3545;font-size:15px;'>"
                        "<i class='fa fa-exclamation-triangle'></i>&nbsp;"
                        "<b>Alerte IA — Incompatibilité détectée</b>"
                        "</span>"
                        "{details}"
                        "<p style='color:#555;margin:4px 0 0;'><i>{reason}</i></p>"
                        "</div>"
                    ).format(details=details, reason=reason))
                else:
                    rec.message_post(body=Markup(
                        "<div style='border-left:4px solid #28a745;padding:8px 12px;background:#f5fff8;border-radius:4px;'>"
                        "<span style='color:#28a745;font-size:15px;'>"
                        "<i class='fa fa-check-circle'></i>&nbsp;"
                        "<b>IA : Document validé</b>"
                        "</span>"
                        "<p style='color:#555;margin:4px 0 0;'>Le document Invoice correspond parfaitement aux informations saisies dans Odoo.</p>"
                        "</div>"
                    ))

            except Exception as e:
                rec.message_post(body=Markup(f"<b>Erreur IA</b> : Une erreur est survenue lors de la communication avec OpenAI : {str(e)}"))
                continue

    legacy_article_id = fields.Many2one('logistique.article', string='Article (Ancien)', readonly=True)
    achat_article_id = fields.Many2one('achat.article', string='Article')
    details = fields.Char(string='Details')

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if self.contract_id:
            self.contract_num = self.contract_id.name
            self.supplier_id = self.contract_id.supplier_id
            self.ste_id = self.contract_id.ste_id
            self.achat_article_id = self.contract_id.article_id
            self.incoterm = self.contract_id.incoterm
            self.details = self.contract_id.details

            self.origin_id = self.contract_id.origin_id
            self.free_time_negotiated = self.contract_id.free_time_negotiated
            # Pre-fill actual free time with negotiated value
            self.free_time = self.contract_id.free_time_negotiated
            if self.contract_id.weight_total:
                self.weight = self.contract_id.weight_total # Optional sync, user might update per shipment

    def action_generate_excel_dossiers_to_exit(self):
        if not xlsxwriter:
            raise ValidationError("La bibliothèque xlsxwriter n'est pas installée.")

        from datetime import datetime, time
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # --- DÉFINITION DES STYLES ---
        header_style = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#D9E1F2', 'font_size': 10, 'text_wrap': True
        })
        
        date_title_style = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#5B9BD5', 'font_size': 14, 'border': 1
        })
        
        supplier_title_style = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#FFE699', 'font_size': 16, 'border': 1
        })
        
        cell_style = workbook.add_format({'border': 1, 'valign': 'vcenter', 'font_size': 9, 'align': 'center'})
        left_align_style = workbook.add_format({'border': 1, 'valign': 'vcenter', 'font_size': 9, 'align': 'left'})
        
        date_style = workbook.add_format({
            'border': 1, 'num_format': 'dd/mm/yyyy', 'align': 'center', 'font_size': 9
        })
        
        num_style = workbook.add_format({
            'border': 1, 'num_format': '#,##0.00', 'align': 'center', 'font_size': 9
        })
        
        pink_num_style = workbook.add_format({
            'border': 1, 'num_format': '#,##0.00', 'align': 'center', 'font_size': 9, 'bg_color': '#FCE4D6'
        })

        footer_label_style = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 10
        })
        
        footer_val_style = workbook.add_format({
            'bold': True, 'border': 1, 'bg_color': '#FF0000', 'font_color': 'white', 'num_format': '#,##0.00', 'font_size': 10, 'align': 'center'
        })
        
        green_obs_style = workbook.add_format({
            'border': 1, 'bg_color': '#C6E0B4', 'font_size': 9, 'align': 'center'
        })
        yellow_obs_style = workbook.add_format({
            'border': 1, 'bg_color': '#FFF2CC', 'font_size': 9, 'align': 'center'
        })

        sheet = workbook.add_worksheet("SUIVI WEEK")

        # Configuration des colonnes
        sheet.set_column('A:A', 18)  # Importer
        sheet.set_column('B:B', 20)  # Exporter
        sheet.set_column('C:C', 5)   # FCL
        sheet.set_column('D:D', 20)  # INV / CONTRACT
        sheet.set_column('E:E', 15)  # PRODUCT
        sheet.set_column('F:F', 20)  # DETAILS
        sheet.set_column('G:H', 12)  # Weight, UP
        sheet.set_column('I:I', 15)  # Total
        sheet.set_column('J:K', 10)  # Incoterm, Franchise
        sheet.set_column('L:L', 6)   # Rest (if used)
        sheet.set_column('M:M', 22)  # Container
        sheet.set_column('N:N', 12)  # ETA
        sheet.set_column('O:O', 20)  # Observation

        # Calcul des dates min et max pour le titre
        etas = [r.eta for r in self if r.eta]
        if etas:
            min_date = min(etas).strftime('%d/%m')
            max_date = max(etas).strftime('%d/%m')
            date_str = f"{min_date} TO {max_date}"
        else:
            date_str = "SEMAINE EN COURS"

        # Titre global dates (Merge A1:O1)
        sheet.merge_range(0, 0, 0, 14, date_str, date_title_style)

        headers = [
            "Ste", "Supplier", "N°CTN", "INVOICE", "PRODUCT", "DETAILS",
            "WEIGHT", "U.P", "TOTAL", "INCOTERM", "FRANCHISE", "", "CONTAINERS", "ETA", "OBSERVATIONS"
        ]
        sheet.write_row(1, 0, headers, header_style)

        row = 2
        
        exporters = self.mapped('supplier_id')
        
        for exporter in exporters:
            # Ligne jaune du Fournisseur
            export_name = str(exporter.name).upper() if exporter else "SANS FOURNISSEUR"
            sheet.merge_range(row, 0, row, 14, export_name, supplier_title_style)
            row += 1

            recs = self.filtered(lambda r: r.supplier_id == exporter)
            exporter_start_row = row + 1
            
            for rec in recs:
                sheet.write(row, 0, rec.ste_id.name or "", cell_style)
                sheet.write(row, 1, rec.supplier_id.name or "", cell_style)
                
                fcl_count = len(rec.container_names.split(',')) if rec.container_names else 1
                sheet.write(row, 2, fcl_count, cell_style)
                
                sheet.write(row, 3, rec.invoice_number or rec.contract_num or "", cell_style)
                sheet.write(row, 4, rec.achat_article_id.name or "", cell_style)
                sheet.write(row, 5, rec.details or "", left_align_style)
                sheet.write(row, 6, float(rec.weight or 0.0), num_style)
                sheet.write(row, 7, float(rec.price_unit or 0.0), num_style)
                sheet.write(row, 8, float(rec.amount_total or 0.0), pink_num_style)
                
                # J: Incoterm
                sheet.write(row, 9, rec.incoterm.upper() if rec.incoterm else "", cell_style)
                # K: Franchise
                sheet.write(row, 10, rec.free_time or "", cell_style)
                # L: Rest (Empty in the image, or shifted)
                sheet.write(row, 11, "", cell_style)
                # M: Container
                sheet.write(row, 12, rec.container_names or "", cell_style)
                
                # N: ETA
                if rec.eta:
                    sheet.write_datetime(row, 13, datetime.combine(rec.eta, time.min), date_style)
                else:
                    sheet.write(row, 13, "", cell_style)
                
                # O: Observation
                obs = rec.exit_comment or ""
                if "dhl" in obs.lower() or "paye" in obs.lower():
                    sheet.write(row, 14, obs.upper(), green_obs_style)
                elif "en cours" in obs.lower():
                    sheet.write(row, 14, obs.upper(), yellow_obs_style)
                else:
                    sheet.write(row, 14, obs.upper(), cell_style)
                
                row += 1

            # Ligne de sous-total par Exportateur
            for c in range(0, 15): 
                sheet.write(row, c, "", footer_label_style) # Apply empty borders to rest of line
            sheet.write(row, 7, "TOTAL", footer_label_style)
            sheet.write_formula(row, 8, f'=SUM(I{exporter_start_row}:I{row})', footer_val_style)
            row += 1

        # --- RÉSUMÉ GLOBAL EN BAS ---
        row += 2
        sheet.merge_range(row, 3, row, 6, "RÉSUMÉ DES DOSSIERS DE LA SEMAINE", supplier_title_style)
        row += 1
        
        sheet.write(row, 3, "FOURNISSEUR", header_style)
        sheet.write(row, 4, "TOTAL FCL", header_style)
        sheet.write(row, 5, "POIDS TOTAL", header_style)
        sheet.write(row, 6, "MONTANT TOTAL", header_style)
        row += 1
        
        grand_fcl = 0
        grand_weight = 0.0
        grand_amount = 0.0

        for exporter in exporters:
            recs = self.filtered(lambda r: r.supplier_id == exporter)
            supp_name = str(exporter.name).upper() if exporter else "SANS FOURNISSEUR"
            supp_fcl = sum(len(r.container_names.split(',')) if r.container_names else 1 for r in recs)
            supp_weight = sum(r.weight or 0.0 for r in recs)
            supp_amount = sum(r.amount_total or 0.0 for r in recs)
            
            sheet.write(row, 3, supp_name, left_align_style)
            sheet.write(row, 4, supp_fcl, cell_style)
            sheet.write(row, 5, supp_weight, num_style)
            sheet.write(row, 6, supp_amount, pink_num_style)
            
            grand_fcl += supp_fcl
            grand_weight += supp_weight
            grand_amount += supp_amount
            row += 1
            
        sheet.write(row, 3, "TOTAL GÉNÉRAL", footer_label_style)
        sheet.write(row, 4, grand_fcl, footer_label_style)
        sheet.write(row, 5, grand_weight, footer_val_style)
        sheet.write(row, 6, grand_amount, footer_val_style)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': "SUIVI_WEEK_LOGISTIQUE.xlsx",
            'datas': file_data,
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
