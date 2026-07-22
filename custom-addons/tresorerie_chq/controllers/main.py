import json
import base64
import requests
from odoo import http, SUPERUSER_ID
from odoo.http import request, Response

class AITrainingExportController(http.Controller):
    @http.route('/tresorerie_chq/export_ai_data', type='http', auth='user')
    def export_ai_data(self, export_type='all', **kwargs):
        domain = []
        if export_type == 'corrected':
            domain = [('is_corrected', '=', True)]
        
        records = request.env['tresorerie_chq.ai.training'].search(domain)
        
        def generate():
            for rec in records:
                if not rec.scan_document or not rec.validated_data:
                    continue
                    
                pdf_b64 = rec.scan_document.decode('utf-8') if isinstance(rec.scan_document, bytes) else rec.scan_document
                doc_type = "chèques" if rec.document_type == 'cheque' else "effets"
                
                prompt_text = f"""Vous êtes un assistant financier. Vous recevez un scan PDF contenant un ou plusieurs {doc_type}.
Votre but est d'extraire les informations pour chaque {doc_type[:-1]} trouvé dans le document.
Il est ABSOLUMENT CRUCIAL que vous retourniez les éléments dans l'ordre exact où ils apparaissent dans le document PDF (de haut en bas, page par page).

Retournez UNIQUEMENT un objet JSON valide, sans markdown, contenant une liste nommée "items".
Pour chaque élément, extrayez :
1. "numero": Le numéro du {doc_type[:-1]} (généralement 7 chiffres ou moin pour un chèque).
2. "montant": Le montant du {doc_type[:-1]} (uniquement des chiffres, ex: 1500.50). ATTENTION : Lisez attentivement le montant écrit en lettres (qui se trouve souvent au milieu du document, en arabe ou en français) et croisez-le avec le montant en chiffres (en haut à droite) pour garantir l'exactitude absolue du montant extrait.
3. "date_echeance": La date d'échéance écrite sur le document, au format YYYY-MM-DD.
4. "banque": Le nom de la banque (à lire souvent dans le logo en HAUT à GAUCHE ou au CENTRE du chèque). Essayez de faire correspondre avec l'une de ces banques : Attijariwafa Bank, Banque Populaire, BMCE, CIH, etc.
5. "porteur": Le nom du titulaire du compte / porteur. C'est le nom imprimé situé en BAS au CENTRE, généralement juste en dessous du "Compte n°". NE CHOISISSEZ PAS le nom de l'agence (qui se trouve à gauche sous "Payable à"). ATTENTION : Retirez ABSOLUMENT toutes les civilités et titres du texte extrait (comme MR, M., MONSIEUR, MME, MADAME, MLLE) pour ne garder strictement que le nom et le prénom.

Exemple de réponse attendue:
{{
  "items": [
    {{
      "numero": "2102888",
      "montant": 18746.43,
      "date_echeance": "2026-05-16",
      "banque": "Attijariwafa Bank",
      "porteur": "Ali Yassine"
    }}
  ]
}}"""
                message = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "Tu es un assistant expert en comptabilité et finance."
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_file",
                                    "filename": "scan.pdf",
                                    "file_data": f"data:application/pdf;base64,{pdf_b64}"
                                },
                                {
                                    "type": "input_text",
                                    "text": prompt_text
                                }
                            ]
                        },
                        {
                            "role": "assistant",
                            "content": rec.validated_data
                        }
                    ]
                }
                yield json.dumps(message, ensure_ascii=False).encode('utf-8') + b'\n'
                
        headers = [
            ('Content-Type', 'application/jsonl'),
            ('Content-Disposition', 'attachment; filename="dataset_finetuning.jsonl"'),
        ]
        return Response(generate(), headers=headers, direct_passthrough=True)

    @http.route('/api/whatsapp/tresorerie_chq/pdf', type='json', auth='public', csrf=False)
    def whatsapp_tresorerie_chq_pdf(self, **kwargs):
        file_name = kwargs.get('file_name', '')
        pdf_base64 = kwargs.get('pdf_base64')
        group_id = kwargs.get('group_id')
        
        if not file_name or not pdf_base64:
            return {"status": "error", "message": "Fichier PDF manquant."}
            
        import re
        from datetime import datetime
        
        # Parse file name: LCN-HAMZA BASSIT-06-07-2026 (1).pdf (allow optional spaces and WhatsApp duplicate suffix)
        match = re.match(r'^\s*(CHQ|LCN)\s*-\s*(.*?)\s*-\s*(\d{2}-\d{2}-\d{4})(?:\s*\(\d+\))?\s*\.pdf\s*$', file_name, re.IGNORECASE)
        if not match:
            return {"status": "error", "message": f"❌ Nom de fichier invalide: {file_name}. Le format doit être TYPE-CLIENT-DD-MM-YYYY.pdf"}
            
        doc_type_str = match.group(1).upper()
        client_name = match.group(2).strip()
        date_str = match.group(3)
        
        payment_type = 'cheque' if doc_type_str == 'CHQ' else 'effet'
        
        try:
            date_obj = datetime.strptime(date_str, '%d-%m-%Y').date()
        except ValueError:
            return {"status": "error", "message": f"❌ Format de date invalide: {date_str}. Attendu: DD-MM-YYYY"}
            
        # Search client
        Client = request.env['tresorerie_chq.client'].sudo()
        client_id = self._robust_client_search(client_name, Client)
                
        if not client_id:
            return {"status": "success", "message": f"❌ Le client '{client_name}' n'a pas été trouvé dans la base de données (ni par recherche floue)."}
            
        # Create paiement
        Paiement = request.env['tresorerie_chq.paiement'].sudo()
        paiement_val = {
            'client_id': client_id.id,
            'payment_type': payment_type,
            'date': date_obj,
            'reception_date': date_obj,
            'scan_document_name': file_name,
            'scan_document': pdf_base64,
            'state': 'draft'
        }
        
        paiement_id = Paiement.create(paiement_val)
        
        client_name_str = client_id.name
        
        # Trigger AI
        try:
            ai_stats = paiement_id.action_parse_pdf_via_ai() or {}
            lines_count = len(paiement_id.cheque_line_ids) if payment_type == 'cheque' else len(paiement_id.effet_line_ids)
            doc_name = "Chèque(s)" if payment_type == 'cheque' else "Effet(s)"
            
            total_expected = ai_stats.get('total_expected', 0)
            
            msg = f"✅ {doc_name} enregistré(s) avec succès pour {client_name_str}.\nL'IA a extrait {lines_count} ligne(s)."
            
            if total_expected > lines_count:
                missing = total_expected - lines_count
                msg += f"\n\n⚠️ ALERTE : L'IA avait détecté un total de {total_expected} {doc_name.lower()} sur le document, mais s'est arrêtée avant la fin (limite mémoire atteinte). Il manque **{missing}** {doc_name.lower()} à saisir manuellement !"
                
            return {"status": "success", "message": msg}
        except Exception as e:
            return {"status": "success", "message": f"⚠️ Document créé pour {client_name_str} mais l'IA a échoué : {str(e)}"}

    @http.route('/api/whatsapp/tresorerie_chq/report', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_tresorerie_chq_report(self, **kwargs):
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)
        
        # 1. Verification of API Key
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'default-secret-key')
        if not api_key or api_key != expected_api_key:
            return {'status': 'error', 'message': 'Unauthorized'}

        try:
            data = kwargs
            message_text = data.get('message', '').strip()
            group_id = data.get('group_id', '')
        except Exception as e:
            return {'status': 'error', 'message': f'Invalid JSON: {str(e)}'}

        if not message_text:
            return {'status': 'error', 'message': 'Empty message'}

        TRESORERIE_REPORT_GROUP_ID = "120363429851164875@g.us"
        if group_id != TRESORERIE_REPORT_GROUP_ID:
            return {'status': 'ignored', 'message': 'This agent only handles the Tresorerie Report Group.'}

        # 1. Fast match & Fuzzy code search
        Client = request.env['tresorerie_chq.client'].sudo()
        client_id = self._robust_client_search(message_text, Client)
        
        if client_id:
            clients = client_id
        else:
            # AI Fallback
            openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
            if not openai_key:
                return {'status': 'error', 'message': 'OpenAI API key not configured (parameter: whatsapp_stock.openai_key)'}

            all_clients = Client.search([])
            client_names_list = [c.name for c in all_clients if c.name]
            
            all_aliases = request.env['tresorerie_chq.client.alias'].sudo().search([])
            alias_list = [f"{a.name} -> {a.client_id.name}" for a in all_aliases if a.client_id]
            
            extracted_name = self._extract_client_name(message_text, openai_key, client_names_list, alias_list)
            
            if not extracted_name or extracted_name.upper() == 'IGNORE':
                return {'status': 'ignored'}

            if not extracted_name or extracted_name.lower() == 'none':
                return {'status': 'not_found', 'message': "Désolé, je n'ai pas pu identifier le client dans votre message."}

            clients = Client.search([
                '|', ('name', 'ilike', extracted_name), ('alias_ids.name', 'ilike', extracted_name)
            ])

        if not clients:
            return {'status': 'not_found', 'message': f"Aucun client trouvé pour : '{message_text}'."}

        if len(clients) > 1:
            absolute_match = clients.filtered(lambda c: c.name.lower() == message_text.lower() or c.name.lower() == extracted_name.lower())
            if absolute_match:
                clients = absolute_match[0]

        if len(clients) == 1:
            client = clients[0]
            report_action = request.env['ir.actions.report'].sudo()
            pdf_content, _ = report_action._render_qweb_pdf('tresorerie_chq.action_report_tresorerie_chq_client_history', res_ids=client.ids)
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            return {
                'status': 'success',
                'client_name': client.name,
                'pdf_base64': pdf_base64,
                'file_name': f"Rapport_Tresorerie_{client.name.replace(' ', '_')}.pdf"
            }
        else:
            choices = [c.name for c in clients]
            choices_text = "Plusieurs clients correspondent à votre demande. Veuillez préciser :\n"
            for i, name in enumerate(choices, 1):
                choices_text += f"{i}- {name}\n"
            return {
                'status': 'multiple_choices',
                'message': choices_text,
                'choices': choices
            }

    def _robust_client_search(self, text, ClientModel):
        import difflib
        import re
        text_clean = text.lower().strip()
        
        # 1. Exact or ILIKE match
        client_id = ClientModel.search([('name', 'ilike', text_clean)], limit=1)
        if client_id:
            return client_id
            
        AliasModel = request.env['tresorerie_chq.client.alias'].sudo()
        alias_id = AliasModel.search([('name', 'ilike', text_clean)], limit=1)
        if alias_id:
            return alias_id.client_id
            
        # 2. Fuzzy match directly in Python (difflib)
        def normalize_str(s):
            return re.sub(r'[\W_]+', '', s.lower()) if s else ''
            
        text_norm = normalize_str(text_clean)
        
        all_clients = ClientModel.search([])
        client_names_norm = {normalize_str(c.name): c for c in all_clients if c.name}
        
        # Check closest client name
        closest_names = difflib.get_close_matches(text_norm, client_names_norm.keys(), n=1, cutoff=0.7)
        if closest_names:
            return client_names_norm[closest_names[0]]
            
        # Check closest alias
        all_aliases = AliasModel.search([])
        alias_names_norm = {normalize_str(a.name): a.client_id for a in all_aliases if a.name and a.client_id}
        
        closest_aliases = difflib.get_close_matches(text_norm, alias_names_norm.keys(), n=1, cutoff=0.7)
        if closest_aliases:
            return alias_names_norm[closest_aliases[0]]
            
        return False

    def _extract_client_name(self, text, api_key, client_names_list, alias_list=None):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        db_names = ", ".join(client_names_list) if client_names_list else "Aucun client disponible"
        synonyms = "\n".join(alias_list) if alias_list else "Aucun synonyme défini."
        
        prompt = (
            "Tu es un assistant administratif. Ta tâche est d'identifier le nom correct du client demandé pour un rapport de trésorerie (chèques/effets).\n"
            "Voici la liste des clients de la base de données :\n"
            f"[{db_names}]\n\n"
            "Voici un dictionnaire d'alias (synonymes) pour t'aider :\n"
            f"{synonyms}\n\n"
            "Message WhatsApp : " + text + "\n\n"
            "Règles strictes :\n"
            "1. Identifie le nom du client mentionné.\n"
            "2. Retourne le nom du client tel qu'il apparaît dans la liste (le plus proche possible).\n"
            "3. IMPORTANT : Si la demande est vague (ex: 'taggada'), renvoie UNIQUEMENT le terme commun.\n"
            "4. IMPORTANT : Si le message ne contient QUE des emojis ou des ponctuations (ex: '???', '...'), réponds UNIQUEMENT 'IGNORE'.\n"
            "5. Pour tout autre message, tente d'identifier le client de la base de données. Si vraiment aucun ne correspond de près ou de loin, réponds 'None'.\n"
            "Retourne UNIQUEMENT le résultat (le nom du client ou IGNORE)."
        )
        data = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0
        }
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        except Exception:
            return None
