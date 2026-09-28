import base64
import logging
import requests
import difflib
from odoo import http, SUPERUSER_ID, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class WhatsAppDouaneController(http.Controller):

    def normalize_ref(self, val):
        """Removes ALL non-alphanumeric characters and converts to uppercase."""
        if not val:
            return ""
        # Keep only A-Z and 0-9
        import re
        return re.sub(r'[^A-Z0-9]', '', str(val).upper())

    def strip_leading_zeros_all(self, val):
        """Removes leading zeros from each numeric segment (e.g. '00123/045' -> '123/45' -> '12345')."""
        if not val:
            return ""
        import re
        val_clean = re.sub(r'(^|[^0-9])0+([0-9]+)', r'\1\2', str(val).strip())
        norm = self.normalize_ref(val_clean)
        return norm.lstrip('0')

    def is_zero_prefix_match(self, s1, s2):
        """
        Returns True if the only difference between normalized s1 and s2
        is leading zeros (at start of string or at start of segments).
        """
        if not s1 or not s2:
            return False
        n1 = self.normalize_ref(s1)
        n2 = self.normalize_ref(s2)
        if not n1 or not n2:
            return False
        if n1 == n2:
            return True
        l1 = n1.lstrip('0')
        l2 = n2.lstrip('0')
        if l1 and l1 == l2:
            return True
        c1 = self.strip_leading_zeros_all(s1)
        c2 = self.strip_leading_zeros_all(s2)
        if c1 and c1 == c2:
            return True
        return False

    def get_char_diff_count(self, s1, s2):
        """Counts differences between two normalized strings."""
        n1 = self.normalize_ref(s1)
        n2 = self.normalize_ref(s2)
        if abs(len(n1) - len(n2)) > 1:
            return 99
        # Basic diff for strings of same length
        if len(n1) == len(n2):
            return sum(1 for a, b in zip(n1, n2) if a != b)
        else:
            # One char difference (addition or subtraction)
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
        if message_text.startswith("🔍 DUM : "):
            forced_type = 'dum'
            message_text = message_text.replace("🔍 DUM : ", "").strip()
        elif message_text.startswith("📦 Lot : "):
            forced_type = 'lot'
            message_text = message_text.replace("📦 Lot : ", "").strip()
        elif message_text.startswith("🚢 BL : "):
            forced_type = 'bl'
            message_text = message_text.replace("🚢 BL : ", "").strip()
        elif message_text.startswith("✅ Oui, c'est : "):
            ref_to_send = message_text.replace("✅ Oui, c'est : ", "").strip()
            return self._send_dum_docs_by_ref(ref_to_send)
        elif message_text.startswith("❌ Non, c'est autre chose"):
            return {'status': 'response', 'response': "Désolé pour la confusion. Veuillez renvoyer la référence exacte."}

        # 4.5 Handle Standalone "DUM", "Lot" or "BL" manually typed
        low_msg = message_text.lower()
        if low_msg == 'dum':
            return {'status': 'response', 'response': "D'accord, veuillez m'envoyer le numéro de la DUM."}
        if low_msg == 'lot':
            return {'status': 'response', 'response': "D'accord, veuillez m'envoyer le numéro du Lot."}
        if low_msg == 'bl':
            return {'status': 'response', 'response': "D'accord, veuillez m'envoyer le numéro du BL."}

        # 5. Extract Reference using OpenAI
        openai_key = request.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not openai_key:
            return {'status': 'error', 'message': 'OpenAI API key not configured'}

        reference = self._extract_reference(message_text, openai_key)
        
        # Fallback for short/medium messages if OpenAI fails or returned IGNORE/NONE
        if (not reference or reference.upper() in ['IGNORE', 'NONE']) and len(message_text) < 25:
            # If it's an alphanumeric string, try it as is
            import re
            if re.match(r'^[A-Z0-9\s/\-_.]+$', message_text.upper()):
                reference = message_text

        if not reference or reference.upper() == 'IGNORE':
            return {'status': 'ignored'}

        if reference.upper() == 'NONE':
            return {'status': 'not_found', 'message': "Désolé, je n'ai pas pu identifier de référence DUM ou BL dans votre message."}

        # 6. Aggressive Search Logic (Priority: DUM -> Lot -> BL)
        norm_target = self.normalize_ref(reference)
        
        # Search with priority
        entry = None
        if forced_type:
            entry = self._find_entry_by_norm_ref(norm_target, forced_type, raw_target=reference)
        else:
            # Priority: DUM -> Lot -> BL
            for t in ['dum', 'lot', 'bl']:
                entry = self._find_entry_by_norm_ref(norm_target, t, raw_target=reference)
                if entry:
                    break

        if entry:
            return self._send_dum_docs_by_object(entry)

        # 7. No exact match found -> Fuzzy Match (1-char diff)
        fuzzy_matches = self._get_fuzzy_matches(norm_target)
        if fuzzy_matches:
            choices = [f"✅ Oui, c'est : {m}" for m in fuzzy_matches]
            choices.append("❌ Non, c'est autre chose")
            
            message = f"Je n'ai pas trouvé '{reference}'. Vouliez-vous dire l'un de ceux-là ?\n\n"
            for i, choice in enumerate(choices, 1):
                message += f"{i}- {choice}\n"
                
            return {
                'status': 'multiple_choices',
                'message': message,
                'choices': choices
            }

        # 8. No match or fuzzy match -> Ask DUM, Lot or BL?
        if forced_type:
            type_label = "une DUM" if forced_type == 'dum' else "un Lot" if forced_type == 'lot' else "un BL"
            return {'status': 'not_found', 'message': f"Je n'ai pas trouvé '{reference}' en tant que {type_label}. Veuillez vérifier la référence."}

        choices = [f"🔍 DUM : {reference}", f"📦 Lot : {reference}", f"🚢 BL : {reference}"]
        message = f"Je n'ai pas trouvé '{reference}'. S'agit-il d'une DUM, d'un Lot ou d'un BL ?\n\n"
        for i, choice in enumerate(choices, 1):
            message += f"{i}- {choice}\n"
            
        return {
            'status': 'multiple_choices',
            'message': message,
            'choices': choices
        }

    def _find_entry_by_norm_ref(self, norm_target, field_type, raw_target=None):
        """Finds logistique.entry by normalizing DB fields with flexible wildcards."""
        if not norm_target:
            return None
            
        field = field_type
        if field_type == 'bl':
            field = 'bl_number'
        
        raw_target = raw_target or norm_target
        norm_clean = norm_target.lstrip('0')
        raw_seg_clean = self.strip_leading_zeros_all(raw_target)

        # Build flexible search patterns
        # 1. Exact flexible search
        search_patterns = []
        if norm_target:
            search_patterns.append('%' + '%'.join(list(norm_target)) + '%')
        
        # 2. Flexible search without leading zeros (matches DB values with or without leading zeros)
        if norm_clean and norm_clean != norm_target:
            search_patterns.append('%' + '%'.join(list(norm_clean)) + '%')
            
        if raw_seg_clean and raw_seg_clean not in (norm_target, norm_clean):
            search_patterns.append('%' + '%'.join(list(raw_seg_clean)) + '%')

        has_tanger_med = field == 'dum' and 'tanger_med_dum' in request.env['logistique.entry']._fields
        search_fields = [field]
        if has_tanger_med:
            search_fields.append('tanger_med_dum')

        conditions = []
        for f in search_fields:
            for pat in search_patterns:
                conditions.append((f, 'ilike', pat))

        if len(conditions) == 1:
            domain = conditions
        elif len(conditions) > 1:
            domain = ['|'] * (len(conditions) - 1) + conditions
        else:
            return None

        candidates = request.env['logistique.entry'].sudo().search(domain, order='id desc')

        def get_field_vals(ent):
            vals = []
            for f in search_fields:
                v = ent[f]
                if v:
                    vals.append(v)
            return vals

        # PASS 1: Strict exact normalized match
        for entry in candidates:
            for val in get_field_vals(entry):
                if self.normalize_ref(val) == norm_target:
                    return entry

        # PASS 2: Match neglecting leading zeros
        for entry in candidates:
            for val in get_field_vals(entry):
                if self.is_zero_prefix_match(norm_target, val) or self.is_zero_prefix_match(raw_target, val):
                    return entry

        # PASS 3: Secondary check: see if the target is a substring of the normalized DB field
        for entry in candidates:
            for val in get_field_vals(entry):
                norm_val = self.normalize_ref(val)
                if norm_target in norm_val:
                    return entry
                if norm_clean and len(norm_clean) >= 4 and norm_clean in norm_val:
                    return entry
                
        return None

    def _get_fuzzy_matches(self, norm_target):
        """Find candidates with 1 character difference."""
        found = []
        # Search recently modified entries for speed
        candidates = request.env['logistique.entry'].sudo().search([
            '|', '|', ('dum', '!=', False), ('bl_number', '!=', False), ('lot', '!=', False)
        ], order='write_date desc', limit=500)
        
        for entry in candidates:
            for field in ['dum', 'bl_number', 'lot']:
                val = entry[field]
                if val:
                    # Ignore if the only difference is leading zeros (already handled directly)
                    if self.is_zero_prefix_match(norm_target, val):
                        continue
                    if self.get_char_diff_count(norm_target, val) == 1:
                        found.append(val)
        
        return list(set(found))[:3] # Limit to 3 closest matches

    def _send_dum_docs_by_ref(self, reference):
        """Find entry by exact or leading-zero match and send docs."""
        norm = self.normalize_ref(reference)
        entry = None
        for t in ['dum', 'lot', 'bl']:
            entry = self._find_entry_by_norm_ref(norm, t, raw_target=reference)
            if entry:
                break
            
        if not entry:
            return {'status': 'not_found', 'message': "Dossier introuvable après confirmation."}
        return self._send_dum_docs_by_object(entry)

    def _send_dum_docs_by_object(self, entry):
        """Extract docs from entry and send to bridge."""
        docs = request.env['douane.document'].sudo().search([
            ('entry_id', '=', entry.id),
            ('type', '=', 'dum')
        ])
        if not docs and entry.dossier_id:
            docs = request.env['douane.document'].sudo().search([
                ('entry_id', 'in', entry.dossier_id.entry_ids.ids),
                ('type', '=', 'dum')
            ])
        if not docs:
            return {'status': 'not_found', 'message': f"Dossier {entry.bl_number} trouvé, mais aucun PDF 'DUM' n'est attaché."}

        files = []
        for doc in docs:
            if doc.file:
                b64 = doc.file.decode('utf-8') if isinstance(doc.file, bytes) else doc.file
                files.append({
                    'pdf_base64': b64,
                    'file_name': doc.file_name or f"DUM_{entry.dum or entry.bl_number}.pdf"
                })
        
        return {
            'status': 'success',
            'product_name': entry.dum or entry.bl_number,
            'files': files
        }

    def _extract_reference(self, text, api_key):
        """Use OpenAI to extract reference with updated instructions."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        prompt = (
            "Tu es un assistant logistique. Ta tâche est d'identifier la référence d'un dossier (DUM, Lot ou BL) mentionnée dans un message WhatsApp.\n"
            "Exemples valides :\n"
            "- DUM : 12345/2026, 610/2025, 331 L\n"
            "- Lot : LOT 123, L-456, 331 L\n"
            "- BL : MEDUT7846505, HLCUBSC2511BEGMO\n\n"
            "Message WhatsApp : " + text + "\n\n"
            "Règles :\n"
            "1. Retourne uniquement la référence brute.\n"
            "2. Ignore les caractères spéciaux et espaces lors de ton analyse mais retourne la référence telle qu'écrite.\n"
            "3. IMPORTANT : Si le message ne contient QUE des symboles/caractères spéciaux sans sens (ex: '???', '...', '---') ou ne contient QUE des emojis (ex: '🚀🚀', '👍'), réponds UNIQUEMENT 'IGNORE'.\n"
            "4. Pour tout autre message qui ressemble à un mot ou une référence (ex: 'Akajo', 'Salut'), tente d'identifier la référence ou réponds 'None' si aucun ne correspond.\n"
            "Retourne UNIQUEMENT le résultat (ou IGNORE)."
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
