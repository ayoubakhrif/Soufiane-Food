import json
from odoo import http
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
        
        # Parse file name: LCN-HAMZA BASSIT-06-07-2026.pdf
        match = re.match(r'^(CHQ|LCN)-(.*?)-(\d{2}-\d{2}-\d{4})\.pdf$', file_name, re.IGNORECASE)
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
        client_id = Client.search([('name', 'ilike', client_name)], limit=1)
        if not client_id:
            return {"status": "success", "message": f"❌ Le client '{client_name}' n'a pas été trouvé dans la base de données."}
            
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
            paiement_id.action_parse_pdf_via_ai()
            lines_count = len(paiement_id.cheque_line_ids) if payment_type == 'cheque' else len(paiement_id.effet_line_ids)
            doc_name = "Chèque(s)" if payment_type == 'cheque' else "Effet(s)"
            return {"status": "success", "message": f"✅ {doc_name} enregistré(s) avec succès pour {client_name_str}.\nL'IA a extrait {lines_count} ligne(s)."}
        except Exception as e:
            return {"status": "success", "message": f"⚠️ Document créé pour {client_name_str} mais l'IA a échoué : {str(e)}"}
