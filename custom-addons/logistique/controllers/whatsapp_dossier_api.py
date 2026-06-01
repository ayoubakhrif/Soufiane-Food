import base64
import json
import logging
import requests
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsappDossierVerificationApi(http.Controller):

    @http.route('/api/whatsapp/dossier_verification', type='json', auth='none', methods=['POST'], csrf=False)
    def handle_dossier_verification(self, **kw):
        """
        Endpoint called by Whatsapp bridge when a series of dashes is received in the verification group.
        It processes all accumulated documents, checks them against document configs, and returns reports.
        """
        try:
            # Check API Key
            api_key = request.httprequest.headers.get('X-Api-Key')
            valid_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'whatsapp_direct_quantity')
            if api_key != valid_api_key:
                return {'error': 'Invalid API Key', 'status': 401}

            documents = kw.get('documents', [])
            if not documents:
                return {
                    'status': 'ignored',
                    'message': 'Aucun document à vérifier.'
                }

            # Prepare OpenAI Call
            openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
            if not openai_key:
                return {
                    'status': 'error',
                    'message': 'Clé OpenAI non configurée.'
                }

            # Fetch document configurations from DB
            configs = request.env['logistique.document.config'].sudo().search([])
            config_desc = "CONFIGURATIONS DISPONIBLES:\n"
            for conf in configs:
                config_desc += f"- {conf.name.upper()} (Code: {conf.name})\n"
                config_desc += "  Champs requis:\n"
                for line in conf.line_ids:
                    linked = f" (Doit correspondre au document: {line.document_type})" if line.document_type else ""
                    config_desc += f"    * {line.name}{linked}\n"
            
            if not configs:
                config_desc = "Aucune configuration de document trouvée dans Odoo."

            prompt_text = f"""Vous êtes un assistant IA de logistique expert en contrôle documentaire. 
L'utilisateur a envoyé un lot de documents liés à UN SEUL dossier logistique.
Votre mission est de vérifier que tous les champs obligatoires sont présents et cohérents entre tous les documents.

{config_desc}

INSTRUCTIONS DE VÉRIFICATION :
1. Pour CHAQUE fichier PDF fourni, vous devez :
   a. L'analyser et déterminer à quel type de configuration il correspond (Code). S'il ne correspond à aucun, marquez-le comme "other".
   b. Extraire la valeur de TOUS les "champs requis" définis dans sa configuration.
   c. Si un champ requis est INTROUVABLE, c'est une erreur.
2. ENSUITE, vous devez vérifier la COHÉRENCE CROISÉE :
   a. Les champs ayant une signification identique (ex: LOT, Numéro d'Invoice, Navire) doivent avoir la même valeur sur tous les documents.
   b. Si un champ requis précise "(Doit correspondre au document: X)", vous devez vérifier que la valeur correspond exactement à la valeur extraite dans le document de type X fourni dans ce lot.
3. RÈGLES DE COMPARAISON : 
   - Soyez tolérant sur la casse, les espaces, et les préfixes (ex: INV-2023 = 2023).
   - Les poids sont en tonnes (MT = T = Tonnes).
   - Veillez à utiliser exactement les mêmes noms de fichiers que ceux fournis dans la liste ci-dessous.

LISTE EXACTE DES FICHIERS FOURNIS :

Format de réponse ATTENDU (JSON uniquement) :
{{
    "documents": [
        {{
            "file_name": "nom exact du fichier",
            "extracted_type": "Code du type de document identifié",
            "fields": [
                {{
                    "name": "Nom du champ requis (ex: LOT)",
                    "status": "present ou absent",
                    "value": "La valeur extraite (vide si absent)"
                }}
            ]
        }}
    ],
    "differences": [
        "Explication claire d'une incohérence entre deux documents, ex: Le 'Container Number' est 'MSKU123' sur INVOICE mais 'MSKU999' sur PACKING."
    ]
}}
"""

            input_contents = []
            
            # Attach PDFs and build file list
            file_list_str = ""
            for doc in documents:
                file_name = doc.get('file_name', 'document.pdf')
                file_list_str += f"- {file_name}\n"
                pdf_b64 = doc.get('pdf_base64')
                if pdf_b64:
                    input_contents.append({
                        "type": "input_file",
                        "filename": file_name,
                        "file_data": f"data:application/pdf;base64,{pdf_b64}"
                    })

            prompt_text += file_list_str + "\nFormat de réponse ATTENDU (JSON uniquement) :\n{\n    \"documents\": [\n        {\n            \"file_name\": \"nom exact du fichier\",\n            \"extracted_type\": \"Code du type de document identifié\",\n            \"fields\": [\n                {\n                    \"name\": \"Nom du champ requis\",\n                    \"status\": \"present ou absent\",\n                    \"value\": \"La valeur extraite (vide si absent)\"\n                }\n            ]\n        }\n    ],\n    \"differences\": [\n        \"Le champ 'LOT' est '123' sur INVOICE mais '456' sur PACKING.\"\n    ]\n}\n"

            # Attach Prompt
            input_contents.append({
                "type": "input_text",
                "text": prompt_text
            })

            payload = {
                "model": "gpt-4o",
                "input": [
                    {
                        "role": "user",
                        "content": input_contents
                    }
                ],
                "text": {
                    "format": {
                        "type": "json_object"
                    }
                },
                "temperature": 0.0,
                "max_output_tokens": 4000
            }

            headers = {
                "Authorization": f"Bearer {openai_key}",
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
                return {
                    'status': 'error',
                    'message': "L'IA n'a retourné aucune réponse."
                }

            result_json = json.loads(raw_content)
            docs_result = result_json.get("documents", [])
            differences = result_json.get("differences", [])
            
            reports = []
            
            for doc_res in docs_result:
                file_name = doc_res.get('file_name')
                extracted_type = doc_res.get('extracted_type', 'Inconnu')
                fields_data = doc_res.get('fields', [])
                
                # Match original doc to get message_key (still useful if we want to log it)
                orig_doc = None
                for d in documents:
                    if d.get('file_name', '').strip().lower() == file_name.strip().lower():
                        orig_doc = d
                        break
                if not orig_doc:
                    for d in documents:
                        if file_name.strip().lower() in d.get('file_name', '').strip().lower() or d.get('file_name', '').strip().lower() in file_name.strip().lower():
                            orig_doc = d
                            break
                            
                message_key = orig_doc.get('message_key') if orig_doc else None
                
                report_text = f"📄 *{file_name}* ({extracted_type.upper()})"
                for f in fields_data:
                    f_name = f.get('name', 'Champ')
                    f_status = f.get('status', 'absent').lower()
                    f_value = f.get('value', '')
                    
                    if f_status == 'present':
                        report_text += f"\n- {f_name} : ✅ Présent" + (f" ({f_value})" if f_value else "")
                    else:
                        report_text += f"\n- {f_name} : ❌ Absent"
                        
                reports.append({
                    'text': report_text,
                    'message_key': message_key
                })

            # Add differences report as a final message if any exist
            if differences:
                diff_text = "⚠️ *DIFFÉRENCES ENTRE LES DOCUMENTS :*\n"
                diff_text += "\n".join([f"🔸 {d}" for d in differences])
                reports.append({
                    'text': diff_text,
                    'message_key': None
                })
            elif len(docs_result) > 1:
                reports.append({
                    'text': "✅ *COHÉRENCE* : Aucune différence détectée entre les documents.",
                    'message_key': None
                })

            return {
                'status': 'success',
                'reports': reports
            }

        except Exception as e:
            _logger.error("Erreur API WhatsApp Dossier Verification : %s", str(e))
            return {
                'status': 'error',
                'message': f"Erreur interne : {str(e)}"
            }
