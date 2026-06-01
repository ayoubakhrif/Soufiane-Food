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

{{
    "documents": [
        {{
            "file_name": "nom exact du fichier",
            "is_valid": true/false,
            "extracted_type": "Code du type de document identifié (ex: invoice, health...)",
            "errors": [
                "Message clair et concis expliquant quel champ manque ou est incohérent, ex: Le champ LOT est absent.",
                "Le Numéro d'Invoice ne correspond pas à la Facture Commerciale jointe."
            ]
        }}
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

            prompt_text += file_list_str + "\nFormat de réponse ATTENDU (JSON uniquement) :\n{\n    \"documents\": [\n        {\n            \"file_name\": \"nom exact du fichier\",\n            \"is_valid\": true/false,\n            \"extracted_type\": \"Code du type de document identifié (ex: invoice, health...)\",\n            \"errors\": [\n                \"Message clair et concis expliquant quel champ manque ou est incohérent, ex: Le champ LOT est absent.\",\n                \"Le Numéro d'Invoice ne correspond pas à la Facture Commerciale jointe.\"\n            ]\n        }\n    ]\n}\n"

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
                "max_output_tokens": 1500
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
            
            reports = []
            
            # Match AI results with the input documents to get the message_key
            for doc_res in docs_result:
                file_name = doc_res.get('file_name')
                is_valid = doc_res.get('is_valid')
                errors = doc_res.get('errors', [])
                extracted_type = doc_res.get('extracted_type', 'Inconnu')
                
                # Find corresponding original document with robust matching
                orig_doc = None
                for d in documents:
                    if d.get('file_name', '').strip().lower() == file_name.strip().lower():
                        orig_doc = d
                        break
                
                if not orig_doc:
                    # Try partial match
                    for d in documents:
                        if file_name.strip().lower() in d.get('file_name', '').strip().lower() or d.get('file_name', '').strip().lower() in file_name.strip().lower():
                            orig_doc = d
                            break
                            
                message_key = orig_doc.get('message_key') if orig_doc else None
                
                if is_valid:
                    report_text = f"✅ *{file_name}* ({extracted_type.upper()})\nDocument validé avec succès ! Tous les champs requis sont présents et cohérents."
                else:
                    err_str = "\n".join([f"❌ {e}" for e in errors])
                    report_text = f"⚠️ *{file_name}* ({extracted_type.upper()})\nErreurs détectées :\n{err_str}"
                    
                reports.append({
                    'text': report_text,
                    'message_key': message_key
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
