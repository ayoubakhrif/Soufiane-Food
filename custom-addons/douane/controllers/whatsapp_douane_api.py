import base64
import logging
import requests
import difflib
from odoo import http, SUPERUSER_ID, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppDouaneController(http.Controller):

    def normalize_ref(self, val):
        """Removes spaces, leading zeros, and returns uppercase string."""
        if not val:
            return ""
        return str(val).replace(' ', '').lstrip('0').upper()

    def get_char_diff_count(self, s1, s2):
        """Counts differences between two strings of same length, or returns distance."""
        n1 = self.normalize_ref(s1)
        n2 = self.normalize_ref(s2)
        if abs(len(n1) - len(n2)) > 1:
            return 99
        # Basic diff for 1-char difference
        if len(n1) == len(n2):
            return sum(1 for a, b in zip(n1, n2) if a != b)
        else:
            # One char more or less
            return 1 if (n1 in n2 or n2 in n1) else 99

    @http.route('/api/whatsapp/douane', type='json', auth='none', methods=['POST'], csrf=False)
    def whatsapp_douane_handler(self, **kwargs):
        # Force database session
        db_name = request.httprequest.args.get('db') or 'soufianefoods'
        request.session.db = db_name
        request.update_env(user=SUPERUSER_ID)

        # 1. API Key Verification
        headers = request.httprequest.headers
        api_key = headers.get('X-Api-Key')
        expected_api_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.api_key', 'whatsapp_direct_quantity')
        
        if not api_key or api_key != expected_api_key:
            _logger.warning("Unauthorized access attempt to WhatsApp Douane API")
            return {'status': 'error', 'message': 'Unauthorized'}

        # 2. Extract Data
        try:
            data = kwargs
            message_text = data.get('message', '').strip()
            group_id = data.get('group_id', '')
        except Exception as e:
            return {'status': 'error', 'message': f'Invalid JSON: {str(e)}'}

        if not message_text:
            return {'status': 'error', 'message': 'Empty message'}

        # 3. Target Group Verification
        DOUANE_GROUP_ID = '120363406635335778@g.us'
        if group_id != DOUANE_GROUP_ID:
            _logger.info(f"Ignoring request from group {group_id} in Douane Agent")
            return {'status': 'ignored', 'message': 'This agent only handles the Douane Group.'}

        # 4. Handle Interactivity / State
        forced_type = None
        if message_text.startswith("🔍 C'est une DUM : "):
            forced_type = 'dum'
            message_text = message_text.replace("🔍 C'est une DUM : ", "").strip()
        elif message_text.startswith("🚢 C'est un BL : "):
            forced_type = 'bl'
            message_text = message_text.replace("🚢 C'est un BL : ", "").strip()
        elif message_text.startswith("✅ Oui, c'est : "):
            ref_to_send = message_text.replace("✅ Oui, c'est : ", "").strip()
            return self._send_dum_docs_by_ref(ref_to_send)
        elif message_text.startswith("❌ Non, c'est autre chose"):
            return {'status': 'response', 'response': "Désolé pour la confusion. Veuillez renvoyer la référence exacte."}

        # 5. Extract Reference using OpenAI
        openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not openai_key:
            return {'status': 'error', 'message': 'OpenAI API key not configured'}

        reference = self._extract_reference(message_text, openai_key)
        
        # Fallback for very short messages if OpenAI fails or returned IGNORE/NONE
        if (not reference or reference.upper() in ['IGNORE', 'NONE']) and len(message_text) < 15:
            # If it's a short alphanumeric string, try it as is
            import re
            if re.match(r'^[A-Z0-9\s/\-_.]+$', message_text.upper()):
                reference = message_text

        if not reference or reference.upper() == 'IGNORE':
            return {'status': 'ignored'}

        if reference.upper() == 'NONE':
            return {'status': 'not_found', 'message': "Désolé, je n'ai pas pu identifier de référence DUM ou BL dans votre message."}

        # 6. Aggressive Search Logic
        norm_target = self.normalize_ref(reference)
        
        # Search with priority
        entry = None
        if forced_type:
            entry = self._find_entry_by_norm_ref(norm_target, forced_type)
        else:
            # Check DUM first
            entry = self._find_entry_by_norm_ref(norm_target, 'dum')
            # Check BL second
            if not entry:
                entry = self._find_entry_by_norm_ref(norm_target, 'bl')

        if entry:
            return self._send_dum_docs_by_object(entry)

        # 7. No exact match found -> Fuzzy Match (1-char diff)
        fuzzy_matches = self._get_fuzzy_matches(norm_target)
        if fuzzy_matches:
            choices = [f"✅ Oui, c'est : {m}" for m in fuzzy_matches]
            choices.append("❌ Non, c'est autre chose")
            return {
                'status': 'multiple_choices',
                'message': f"Je n'ai pas trouvé '{reference}'. Vouliez-vous dire l'un de ceux-là ?",
                'choices': choices
            }

        # 8. No match or fuzzy match -> Ask DUM or BL?
        return {
            'status': 'multiple_choices',
            'message': f"Je n'ai pas trouvé '{reference}'. S'agit-il d'une DUM ou d'un BL ?",
            'choices': [f"🔍 C'est une DUM : {reference}", f"🚢 C'est un BL : {reference}"]
        }

    def _find_entry_by_norm_ref(self, norm_target, field_type):
        """Finds logistique.entry by normalizing DB fields."""
        field = 'dum' if field_type == 'dum' else 'bl_number'
        # Optimization: use ilike with first characters to limit result set
        search_hint = norm_target[:4] if len(norm_target) > 4 else norm_target
        domain = [(field, 'ilike', search_hint)]
        
        candidates = request.env['logistique.entry'].sudo().search(domain)
        for entry in candidates:
            if self.normalize_ref(entry[field]) == norm_target:
                return entry
        return None

    def _get_fuzzy_matches(self, norm_target):
        """Find candidates with 1 character difference."""
        found = []
        # Search recently modified entries for speed
        candidates = request.env['logistique.entry'].sudo().search([
            '|', ('dum', '!=', False), ('bl_number', '!=', False)
        ], order='write_date desc', limit=500)
        
        for entry in candidates:
            for field in ['dum', 'bl_number']:
                val = entry[field]
                if val and self.get_char_diff_count(norm_target, val) == 1:
                    found.append(val)
        
        return list(set(found))[:3] # Limit to 3 closest matches

    def _send_dum_docs_by_ref(self, reference):
        """Find entry by exact string match and send docs."""
        entry = request.env['logistique.entry'].sudo().search([
            '|', ('dum', '=', reference), ('bl_number', '=', reference)
        ], limit=1)
        if not entry:
            # Try one last aggressive search
            norm = self.normalize_ref(reference)
            entry = self._find_entry_by_norm_ref(norm, 'dum')
            if not entry: entry = self._find_entry_by_norm_ref(norm, 'bl')
            
        if not entry:
            return {'status': 'not_found', 'message': "Dossier introuvable après confirmation."}
        return self._send_dum_docs_by_object(entry)

    def _send_dum_docs_by_object(self, entry):
        """Extract docs from entry and send to bridge."""
        docs = request.env['douane.document'].sudo().search([
            ('entry_id', '=', entry.id),
            ('type', '=', 'dum')
        ])
        if not docs:
            return {'status': 'not_found', 'message': f"Dossier {entry.bl_number} trouvé, mais aucun PDF 'DUM' n'est attaché."}

        files = []
        for doc in docs:
            if doc.file:
                files.append({
                    'pdf_base64': doc.file.decode('utf-8'),
                    'file_name': doc.file_name or f"DUM_{entry.dum or entry.bl_number}.pdf"
                })
        
        return {
            'status': 'success',
            'product_name': entry.dum or entry.bl_number,
            'files': files
        }

    def _extract_reference(self, text, api_key):
        """Use OpenAI to extract DUM or BL reference with updated examples."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        prompt = (
            "Tu es un assistant logistique. Ta tâche est d'identifier la référence d'un dossier mentionnée dans un message WhatsApp.\n"
            "Exemples de formats valides :\n"
            "- DUM : 12345/2026, 610/2025, 331 L, 00313 L, 313 L\n"
            "- BL : MEDUT7846505, MSCU1234567, 331 L (un BL peut aussi ressembler à une DUM)\n\n"
            "Message WhatsApp : " + text + "\n\n"
            "Règles :\n"
            "1. Identifie la référence la plus probable.\n"
            "2. Retourne uniquement la référence brute (ex: '331 L').\n"
            "3. Les zéros au début ou les espaces importent peu, retourne ce que tu vois.\n"
            "4. Si le message est trop vague ou ne contient rien d'utile, réponds 'IGNORE' ou 'None'.\n"
            "Retourne UNIQUEMENT le résultat."
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
        except Exception as e:
            _logger.error(f"OpenAI Douane Reference Extraction Error: {str(e)}")
            return None
