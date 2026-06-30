from odoo import models, fields, api
import json
import base64

class TresorerieChqAITrainingExport(models.TransientModel):
    _name = 'tresorerie_chq.ai.training.export'
    _description = "Assistant d'export pour le Fine-Tuning IA"

    export_type = fields.Selection([
        ('corrected', 'Uniquement les données corrigées (Option A)'),
        ('all', 'Toutes les données (Option B)'),
    ], string='Type d\'export', required=True, default='all',
        help="Il est souvent recommandé de fournir un mix (Toutes les données) pour ne pas que l'IA oublie les cas simples.")

    file_data = fields.Binary(string='Fichier JSONL', readonly=True)
    file_name = fields.Char(string='Nom du fichier', readonly=True)
    state = fields.Selection([('choose', 'Choix'), ('get', 'Terminé')], default='choose')

    def action_export(self):
        domain = []
        if self.export_type == 'corrected':
            domain = [('is_corrected', '=', True)]
        
        records = self.env['tresorerie_chq.ai.training'].search(domain)
        
        jsonl_lines = []
        
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
            
            # Note: For OpenAI fine-tuning, since they don't natively support PDF in vision fine-tuning yet,
            # this dataset maintains the structure sent to your custom endpoint so you can train appropriately
            # or convert PDFs to images if needed before uploading to OpenAI.
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
            jsonl_lines.append(json.dumps(message, ensure_ascii=False))
            
        file_content = "\n".join(jsonl_lines)
        file_content_b64 = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
        
        self.write({
            'state': 'get',
            'file_data': file_content_b64,
            'file_name': 'dataset_finetuning.jsonl'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tresorerie_chq.ai.training.export',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
