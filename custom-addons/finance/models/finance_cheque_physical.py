from odoo import models, fields, api

class FinanceChequePhysical(models.Model):
    _name = 'finance.cheque.physical'
    _description = 'Chèque Physique'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name_custom'

    active = fields.Boolean(string='Actif', default=True)
    name = fields.Char(string='N° Chèque', required=True, index=True, tracking=True)
    ste_id = fields.Many2one('finance.ste', string='Société', required=True, tracking=True)
    
    datacheque_ids = fields.One2many('datacheque', 'physical_cheque_id', string='Répartitions (Datacheque)')
    
    amount_total = fields.Float(string='Montant Total', compute='_compute_amount_total', store=True, tracking=True)
    
    # Computed fields from the first linked datacheque (source of truth for shared data)
    date_emission = fields.Date(string="Date d'émission", compute='_compute_shared_info', store=True)
    date_echeance = fields.Date(string="Date d'échéance", compute='_compute_shared_info', store=True)
    date_encaissement = fields.Date(string="Date d'encaissement", compute='_compute_shared_info', store=True)
    benif_id = fields.Many2one('finance.benif', string='Bénéficiaire', compute='_compute_shared_info', store=True)
    
    credit = fields.Float(string="Crédit", compute='_compute_credit_debit')
    debit = fields.Float(string="Encaissement", compute='_compute_credit_debit')
    
    display_name_custom = fields.Char(string="Nom complet", compute='_compute_display_name_custom', store=True)
    
    encours = fields.Selection([
        ('encaisse', 'Encaissé'),
        ('non_encaisse', 'Non encaissé'),
    ], string='Status Encaissement', compute='_compute_encours', store=True)

    # ------------------------------------------------------------
    # DOCUMENTS PDF EN BASE
    # ------------------------------------------------------------
    chq_vide_pdf = fields.Binary(string='Chèque vide (PDF)', attachment=True, tracking=True)
    chq_vide_filename = fields.Char(string='Nom du fichier Chèque vide')
    
    doc_pdf = fields.Binary(string='Documentation (PDF)', attachment=True, tracking=True)
    doc_filename = fields.Char(string='Nom du fichier Documentation')
    
    cheque_copy_pdf = fields.Binary(
        string="Chèque (PDF)",
        attachment=True,
        tracking=True,
        help="PDF de la copie physique du chèque"
    )
    cheque_copy_filename = fields.Char(string="Nom du fichier Chèque")


    # ------------------------------------------------------------
    # FLAG IA
    # ------------------------------------------------------------
    is_fault = fields.Boolean(
        string='Faux',
        default=False,
        tracking=True,
        help="Coché automatiquement par l'IA si la copie du chèque ne correspond pas aux données saisies. L'admin peut le décocher manuellement."
    )

    _sql_constraints = [
        ('unique_chq_ste', 'unique(name, ste_id)', 'Ce chèque physique existe déjà pour cette société.')
    ]

    @api.depends('name', 'ste_id', 'amount_total')
    def _compute_display_name_custom(self):
        for rec in self:
            amount_str = "{:,.2f}".format(rec.amount_total).replace(',', ' ')
            rec.display_name_custom = f"CHQ {rec.name} - {rec.ste_id.name} ({amount_str} MAD)"

    @api.depends('datacheque_ids.amount')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.datacheque_ids.mapped('amount'))

    @api.depends('datacheque_ids', 'datacheque_ids.date_emission', 'datacheque_ids.date_echeance', 'datacheque_ids.benif_id', 'datacheque_ids.date_encaissement')
    def _compute_shared_info(self):
        for rec in self:
            if rec.datacheque_ids:
                # Take info from the first one found (assuming they should be consistent for the same physical cheque)
                first = rec.datacheque_ids[0]
                rec.date_emission = first.date_emission
                rec.date_echeance = first.date_echeance
                rec.benif_id = first.benif_id
                # Search for the first non-empty cashing date among splits
                rec.date_encaissement = next((d.date_encaissement for d in rec.datacheque_ids if d.date_encaissement), False)
            else:
                rec.date_emission = False
                rec.date_echeance = False
                rec.benif_id = False
                rec.date_encaissement = False

    @api.depends('amount_total', 'datacheque_ids.amount', 'datacheque_ids.encours', 'datacheque_ids.date_encaissement')
    def _compute_credit_debit(self):
        for rec in self:
            rec.credit = rec.amount_total or 0.0
            total_debit = 0.0
            if rec.datacheque_ids:
                for split in rec.datacheque_ids:
                    if split.date_encaissement:
                        total_debit += split.amount
            rec.debit = total_debit

    @api.depends('datacheque_ids.encours', 'datacheque_ids.date_encaissement')
    def _compute_encours(self):
        for rec in self:
            # If ANY of the splits is 'encaisse', we consider the physical cheque as encaisse?
            # Or ALL? Usually, a physical cheque is cashed once.
            # If it's split, all splits should share the same status technically.
            # We take the status of the first one found that is encaisse, or default to non_encaisse
            
            # Logic: If any datacheque has date_encaissement, then physical is 'encaisse'
            if any(d.date_encaissement for d in rec.datacheque_ids):
                rec.encours = 'encaisse'
            else:
                rec.encours = 'non_encaisse'

    # ------------------------------------------------------------
    # VÉRIFICATION IA — Copie physique du chèque
    # ------------------------------------------------------------
    def action_verify_cheque_ai(self):
        self.ensure_one()

        if not self.cheque_copy_pdf:
            from odoo.exceptions import ValidationError as VE
            raise VE("Aucune copie PDF du chèque n'est attachée à cet enregistrement. Veuillez d'abord uploader le PDF dans l'onglet 'Copie Chèque'.")

        api_key = self.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not api_key:
            from odoo.exceptions import ValidationError as VE
            raise VE("La clé API OpenAI n'est pas configurée dans les Paramètres Système sous 'whatsapp_stock.openai_key'.")

        import requests
        import json
        from markupsafe import Markup

        # Le fichier binaire est déjà stocké en base64 dans Odoo
        pdf_b64 = self.cheque_copy_pdf.decode('utf-8') if isinstance(self.cheque_copy_pdf, bytes) else self.cheque_copy_pdf

        # Résoudre le nom légal complet de la société :
        societe_legale = ""
        if self.ste_id:
            if self.ste_id.raison_social:
                societe_legale = self.ste_id.raison_social
            elif self.ste_id.core_ste_id and self.ste_id.core_ste_id.name:
                societe_legale = self.ste_id.core_ste_id.name
            else:
                societe_legale = self.ste_id.name

        # Données à vérifier
        data_to_verify = {
            "chq": self.name or "",
            "amount": self.amount_total or 0.0,
            "beneficiaire": self.benif_id.name if self.benif_id else "",
            "date_emission": str(self.date_emission) if self.date_emission else "",
            "societe": societe_legale,
        }

        # Construire uniquement les champs non-vides
        fields_to_check = []
        if data_to_verify["chq"]:
            fields_to_check.append(f"- Numéro de chèque : '{data_to_verify['chq']}'")
        if data_to_verify["amount"]:
            fields_to_check.append(f"- Montant total : {data_to_verify['amount']} MAD (peut apparaître comme DH, MAD, ou sans unité)")
        if data_to_verify["beneficiaire"]:
            fields_to_check.append(f"- Bénéficiaire (à l'ordre de) : '{data_to_verify['beneficiaire']}'")
        if data_to_verify["date_emission"]:
            fields_to_check.append(f"- Date d'émission : '{data_to_verify['date_emission']}' (format YYYY-MM-DD, comparer avec la date sur le chèque)")
        if data_to_verify["societe"]:
            fields_to_check.append(f"- Société émettrice (raison sociale) : '{data_to_verify['societe']}'")

        if not fields_to_check:
            from odoo.exceptions import ValidationError as VE
            raise VE("Aucun champ renseigné à vérifier. Veuillez saisir au minimum le numéro et le montant.")

        fields_str = "\n".join(fields_to_check)

        prompt_text = f"""Vous êtes un agent de contrôle financier. Lisez attentivement la copie du chèque joint (PDF).

Voici les informations saisies dans le système pour CE chèque physique (qui peut correspondre à plusieurs paiements répartis). Vérifiez UNIQUEMENT les champs listés ci-dessous :

{fields_str}

RÈGLES DE COMPARAISON STRICTES :
1. NUMÉRO : Comparez les 7 chiffres du numéro de chèque tel qu'il apparaît sur le chèque (zone MICR ou corps du chèque).
2. MONTANT : Valeurs équivalentes : 100000 = 100,000 = 100.000 = 100 000 MAD = 100 000 DH. Ignorez les séparateurs de milliers.
3. TEXTE (bénéficiaire, société) : Insensible à la casse, ignorez espaces/tirets/points superflus.
4. DATE : Comparez la date d'émission au format jour/mois/année sur le chèque avec la date système.
5. BÉNÉFICE DU DOUTE : Si l'information est partiellement lisible ou absente du PDF, considérez-la comme CORRECTE. Ne signalez une erreur que si vous êtes CERTAIN à 100% qu'il y a une différence réelle.
6. CHAMPS ABSENTS DU PDF : Si un champ n'apparaît pas clairement dans le document, ignorez-le.

Répondez UNIQUEMENT avec du JSON valide, sans explication, sans markdown :
{{
    "is_fault": true,
    "mismatches": [
        {{"field": "nom du champ", "odoo_value": "valeur Odoo", "pdf_value": "valeur trouvée dans le PDF"}}
    ],
    "reason": "Résumé en français des incompatibilités trouvées."
}}
OU si tout est correct :
{{
    "is_fault": false,
    "mismatches": [],
    "reason": ""
}}"""

        # Utilisation de l'API Responses OpenAI
        payload = {
            "model": "gpt-4o",
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": self.cheque_copy_filename or "cheque.pdf",
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

        try:
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
                from odoo.exceptions import ValidationError as VE
                raise VE("OpenAI n'a retourné aucune réponse. Vérifiez le fichier PDF.")

            result = json.loads(raw_content)

            is_fault_val = result.get("is_fault", False)
            reason = result.get("reason", "")
            mismatches = result.get("mismatches", [])

            self.sudo().write({'is_fault': is_fault_val})

            if is_fault_val:
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

                self.message_post(body=Markup(
                    "<div style='border-left:4px solid #dc3545;padding:8px 12px;background:#fff5f5;border-radius:4px;'>"
                    "<span style='color:#dc3545;font-size:15px;'>"
                    "<i class='fa fa-exclamation-triangle'></i>&nbsp;"
                    "<b>Alerte IA — Incompatibilité détectée sur la copie du chèque physique</b>"
                    "</span>"
                    "{details}"
                    "<p style='color:#555;margin:4px 0 0;'><i>{reason}</i></p>"
                    "</div>"
                ).format(details=details, reason=reason))
            else:
                self.message_post(body=Markup(
                    "<div style='border-left:4px solid #28a745;padding:8px 12px;background:#f5fff8;border-radius:4px;'>"
                    "<span style='color:#28a745;font-size:15px;'>"
                    "<i class='fa fa-check-circle'></i>&nbsp;"
                    "<b>IA : Chèque physique validé ✅</b>"
                    "</span>"
                    "<p style='color:#555;margin:4px 0 0;'>La copie du chèque correspond aux informations agrégées dans Odoo.</p>"
                    "</div>"
                ))

        except requests.exceptions.HTTPError as e:
            err_body = ""
            try:
                err_body = e.response.json().get("error", {}).get("message", "")
            except Exception:
                pass
            from odoo.exceptions import ValidationError as VE
            raise VE(f"Erreur OpenAI ({e.response.status_code}) : {err_body or str(e)}")
        except Exception as e:
            from odoo.exceptions import ValidationError as VE
            raise VE(f"Erreur lors de la communication avec OpenAI : {str(e)}")

    def action_reset_fault(self):
        """Permet à un manager Finance de réinitialiser manuellement le flag is_fault."""
        self.ensure_one()
        from markupsafe import Markup
        self.sudo().write({'is_fault': False})
        self.message_post(body=Markup(
            "<div style='border-left:4px solid #6c757d;padding:8px 12px;background:#f8f9fa;border-radius:4px;'>"
            "<span style='color:#6c757d;font-size:15px;'>"
            "<i class='fa fa-undo'></i>&nbsp;"
            "<b>Flag 'Faux' réinitialisé manuellement par un manager</b>"
            "</span>"
            "</div>"
        ))
