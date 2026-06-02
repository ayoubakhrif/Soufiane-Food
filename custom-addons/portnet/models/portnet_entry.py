from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PortnetEntry(models.Model):
    _name = 'portnet.entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Entrée Portnet'
    _order = 'id desc'

    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        default='/',
        tracking=True,
    )

    article_id = fields.Many2one(
        'achat.article',
        string='Article',
        required=True,
        tracking=True,
    )

    origin_id = fields.Many2one(
        'achat.origin',
        string='Origine',
        required=True,
        tracking=True,
    )

    supplier_id = fields.Many2one(
        'logistique.supplier',
        string='Fournisseur',
        required=True,
        tracking=True,
    )

    incoterm = fields.Selection(
        selection=[
            ('cfr', 'CFR'),
            ('fob', 'FOB'),
            ('exw', 'EXW'),
        ],
        string='Incoterm',
        required=True,
        tracking=True,
    )

    invoice = fields.Char(
        string='Facture',
        required=True,
        tracking=True,
    )

    ste_id = fields.Many2one(
        'logistique.ste',
        string='Société',
        required=True,
        tracking=True,
    )

    note = fields.Text(
        string='Notes',
        tracking=True,
    )

    provenance = fields.Many2one(
        'achat.origin',
        string='Provenance',
        required=True,
        tracking=True,
    )

    device = fields.Selection(
        selection=[
            ('usd', 'USD'),
            ('eur', 'EUR'),
        ],
        string='Devise',
        required=True,
        tracking=True,
    )

    gross = fields.Float(string='Poids brut (kg)', required=True, tracking=True)
    net = fields.Float(string='Poids net (kg)', required=True, tracking=True)
    valeur = fields.Float(string='Valeur', required=True, tracking=True)
    nomenclature = fields.Char(string='Nomenclature', tracking=True)
    avance = fields.Float(string='Avance', tracking=True)

    total_fob = fields.Float(string='Total FOB', required=True, tracking=True)
    total_freight = fields.Float(string='Total Freight', tracking=True)  # required only when incoterm=cfr (enforced in view)

    total_cfr = fields.Float(
        string='Total CFR',
        compute='_compute_total_cfr',
        store=True,
        tracking=True,
    )

    payment_terms = fields.Boolean(string='Payment terms', tracking=True)
    date_invoice = fields.Date(string='Date facture', required=True, tracking=True)

    state = fields.Selection(
        selection=[
            ('new', 'Nouveau'),
            ('domicilied', 'Validé'),
            ('regle', 'Domicilié'),
            ('annule', 'Annulé'),
        ],
        string='État',
        default='new',
        tracking=True,
    )

    portnet_pdf = fields.Binary(string='Dossier de portnet (PDF)', attachment=True)
    portnet_pdf_name = fields.Char(string='Nom du PDF')

    is_faux = fields.Boolean(
        string='Faux',
        default=False,
        tracking=True,
        help="Coché automatiquement par l'IA si le PDF ne correspond pas aux données."
    )

    ai_status = fields.Selection([
        ('unverified', 'Non vérifié'),
        ('validated', 'Validé'),
        ('error', 'Erreur')
    ], string='Statut IA', default='unverified', tracking=True)

    # ── Computed ─────────────────────────────────────────────────────────────

    @api.depends('total_fob', 'total_freight')
    def _compute_total_cfr(self):
        for rec in self:
            rec.total_cfr = rec.total_fob + rec.total_freight

    @api.onchange('article_id')
    def _onchange_article_id(self):
        if self.article_id:
            company_article = self.article_id.company_article_id
            if company_article:
                self.nomenclature = company_article.nomenclature

    @api.constrains('invoice')
    def _check_unique_invoice(self):
        for rec in self:
            if rec.invoice:
                domain = [('invoice', '=', rec.invoice), ('id', '!=', rec.id)]
                if self.search_count(domain) > 0:
                    raise ValidationError("La facture '%s' a déjà été saisie dans un autre enregistrement." % rec.invoice)

    # ── Valeur validation (only called on Domicilier) ───────────────────────

    def _check_valeur(self):
        """Block the Domicilier transition when valeur differs from the
        article's reference value stored in company.article.value,
        based on user groups:
        - Admin: Always allowed
        - Manager: Allowed if valeur <= ref_value
        - User: Allowed only if valeur == ref_value
        """
        for rec in self:
            if not rec.article_id:
                continue
            company_article = rec.article_id.company_article_id
            if not company_article:
                continue
            ref_value = company_article.value
            # Only enforce when a reference value has been set (> 0)
            if not ref_value:
                continue

            # 1. Admins: Always allowed
            if self.env.user.has_group('portnet.group_portnet_admin'):
                if rec.valeur != ref_value:
                    rec.message_post(body="Domiciliation effectuée par un administrateur malgré une différence de valeur par rapport aux données société.")
                continue

            # 2. Managers: Allowed if <= ref_value
            if self.env.user.has_group('portnet.group_portnet_manager'):
                if rec.valeur > ref_value:
                    raise ValidationError(
                        "En tant que Responsable Portnet, vous ne pouvez pas domicilier "
                        "une valeur (%.2f) strictement supérieure à la valeur "
                        "de référence de l'article \"%s\" (%.2f).\n"
                        "Veuillez corriger la valeur ou demander à un administrateur."
                        % (rec.valeur, company_article.display_name, ref_value)
                    )
                continue

            # 3. Normal Users: Allowed ONLY if == ref_value
            if rec.valeur != ref_value:
                raise ValidationError(
                    "La valeur saisie (%.2f) doit être égale à la valeur "
                    "de référence de l'article \"%s\" (%.2f).\n"
                    "Veuillez corriger la valeur pour domicilier."
                    % (rec.valeur, company_article.display_name, ref_value)
                )

    # ── State transitions ─────────────────────────────────────────────────────

    def action_domicilier(self):
        self.ensure_one()
        if self.env.user.has_group('portnet.group_portnet_admin'):
            if not self.env.context.get('bypass_valeur_wizard'):
                if self.article_id and self.article_id.company_article_id:
                    ref_value = self.article_id.company_article_id.value
                    if ref_value and self.valeur != ref_value:
                        return {
                            'name': 'Confirmation Domiciliation',
                            'type': 'ir.actions.act_window',
                            'res_model': 'portnet.confirm.wizard',
                            'view_mode': 'form',
                            'target': 'new',
                            'context': {
                                'default_entry_id': self.id,
                                'default_message': "La valeur saisie (%.2f) est différente de la valeur de référence de l'article (%.2f).\nVoulez-vous vraiment domicilier ce dossier ?" % (self.valeur, ref_value)
                            }
                        }
        
        self._check_valeur()
        self.write({'state': 'domicilied'})

    def action_regler(self):
        self.write({'state': 'regle'})

    def action_annuler(self):
        self.write({'state': 'annule'})

    def action_reset_new(self):
        self.write({'state': 'new'})

    def action_verify_portnet_ai(self):
        """Verify Portnet entries using AI for uploaded PDF."""
        api_key = self.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not api_key:
            raise ValidationError("La clé API OpenAI n'est pas configurée dans les Paramètres Système sous 'whatsapp_stock.openai_key'.")

        import requests
        import json
        from markupsafe import Markup

        for rec in self:
            if not rec.portnet_pdf:
                rec.message_post(body=Markup("<b>Saut de la vérification IA</b> : Aucun PDF 'Dossier de portnet' n'est attaché à ce dossier."))
                continue

            try:
                pdf_bytes = rec.portnet_pdf
                pdf_b64 = pdf_bytes.decode('utf-8') if isinstance(pdf_bytes, bytes) else pdf_bytes

                data_to_verify = {
                    "reference": rec.name or "",
                    "invoice": rec.invoice or "",
                    "gross_weight": rec.gross or 0.0,
                    "net_weight": rec.net or 0.0,
                    "valeur": rec.valeur or 0.0,
                    "device": dict(rec._fields['device'].selection).get(rec.device) if rec.device else "",
                    "incoterm": rec.incoterm.upper() if rec.incoterm else "",
                    "total_fob": rec.total_fob or 0.0,
                    "total_cfr": rec.total_cfr or 0.0,
                }

                fields_to_check = []
                if data_to_verify["reference"] and data_to_verify["reference"] != "/":
                    fields_to_check.append(f"- Référence : '{data_to_verify['reference']}'")
                if data_to_verify["invoice"]:
                    fields_to_check.append(f"- Facture : '{data_to_verify['invoice']}'")
                if data_to_verify["gross_weight"]:
                    fields_to_check.append(f"- Poids brut : {data_to_verify['gross_weight']} kg")
                if data_to_verify["net_weight"]:
                    fields_to_check.append(f"- Poids net : {data_to_verify['net_weight']} kg")
                if data_to_verify["valeur"]:
                    fields_to_check.append(f"- Valeur : {data_to_verify['valeur']}")
                if data_to_verify["device"]:
                    fields_to_check.append(f"- Devise : '{data_to_verify['device']}'")
                if data_to_verify["incoterm"]:
                    fields_to_check.append(f"- Incoterm : '{data_to_verify['incoterm']}'")
                if data_to_verify["total_fob"]:
                    fields_to_check.append(f"- Total FOB : {data_to_verify['total_fob']}")
                if data_to_verify["total_cfr"]:
                    fields_to_check.append(f"- Total CFR : {data_to_verify['total_cfr']}")

                if not fields_to_check:
                    rec.message_post(body=Markup("<b>Saut de la vérification IA</b> : Aucun champ renseigné à vérifier."))
                    continue

                fields_str = "\n".join(fields_to_check)

                prompt_text = f"""Vous êtes un agent de contrôle douanier et logistique. Lisez attentivement le document PDF "Dossier de portnet" joint.

Voici les informations saisies dans le système pour ce dossier. Vérifiez UNIQUEMENT les champs listés ci-dessous :

{fields_str}

RÈGLES DE COMPARAISON STRICTES :
1. TEXTE (Facture, Devise, Incoterm, etc.) : Comparez sans tenir compte de la casse et en ignorant les espaces, tirets, points, slashes. Considérez que c'est une CORRESPONDANCE si le numéro Odoo est la partie principale du numéro PDF.
2. NOMBRES (Poids, Valeur, Totaux) : Les nombres peuvent être formatés différemment (ex: 80300 = 80,300 = 80.300).
3. BÉNÉFICE DU DOUTE : Soyez très tolérant. Ne mettez is_faux=true que si les chiffres sont totalement différents et sans aucun lien logique.
4. CHAMPS ABSENTS : Si un champ n'apparaît pas clairement dans le document, ignorez-le (ne le considérez pas comme faux).

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

                payload = {
                    "model": "gpt-4o",
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_file",
                                    "filename": rec.portnet_pdf_name or "portnet.pdf",
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
                    rec.ai_status = 'error'
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
                        "<p style='color:#555;margin:4px 0 0;'>Le document PDF correspond aux informations saisies dans Odoo.</p>"
                        "</div>"
                    ))

            except Exception as e:
                rec.message_post(body=Markup(f"<b>Erreur IA</b> : Une erreur est survenue lors de la communication avec OpenAI : {str(e)}"))
                rec.ai_status = 'error'
                continue