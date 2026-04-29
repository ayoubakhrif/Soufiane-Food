import json
import logging
import difflib
import re

from odoo import models, api

_logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """Tu es un assistant qui analyse des messages utilisateur liés à la gestion de stock.
Tu dois extraire l'intention et les paramètres de la question.

Réponds UNIQUEMENT en JSON valide, sans aucun texte autour.

Intentions possibles :
- "stock_order_validation" : l'utilisateur envoie un message multi-ligne avec des articles, quantités et lots à vérifier.
- "unknown" : le message est du "bruit" total (uniquement des emojis, ou uniquement des caractères aléatoires sans sens).

Format de réponse pour "stock_order_validation":
{
  "intent": "stock_order_validation",
  "items": [
    {"qty": 100, "product": "nom du produit", "lot": "numéro brute (ex: '1warehouse', 'Gacp/122025', '225-25 B')"},
    ...
  ]
}

Règles d'extraction du Lot :
- Le lot peut suivre "lot:", "lot ", "lot", "L:", "L ".
- Il n'y a pas toujours d'espace après "lot:" (ex: "lot:123" -> lot is "123").
- Le lot est souvent ALPHANUMÉRIQUE et peut contenir des caractères comme "/", "-", " ". Capture TOUT le lot.

Exemples :
- "100 amande lot:Gacp/123" → {"intent": "stock_order_validation", "items": [{"qty": 100, "product": "amande", "lot": "Gacp/123"}]}
- "50 lwz lot 225-B mp-07" → {"intent": "stock_order_validation", "items": [{"qty": 50, "product": "lwz", "lot": "225-B mp-07"}]}
"""

class CasaStockChatbot(models.AbstractModel):
    _name = 'casa.stock.chatbot'
    _description = 'Casa Stock Chatbot Engine'

    @api.model
    def _get_openai_client(self):
        """Get an OpenAI client using the API key from system parameters."""
        api_key = self.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not api_key:
            _logger.error("OpenAI API key not configured (whatsapp_stock.openai_key)")
            return None
        try:
            from openai import OpenAI
            return OpenAI(api_key=api_key)
        except ImportError:
            _logger.error("openai Python package is not installed")
            return None

    @api.model
    def _get_product_list_text(self):
        """Fetch all product names and their aliases from company articles."""
        # Using company.article as it holds the alias_ids
        articles = self.env['company.article'].sudo().search([])
        lines = []
        for a in articles:
            aliases = a.alias_ids.mapped('name')
            if aliases:
                lines.append(f"{a.display_name} ({', '.join(aliases)})")
            else:
                lines.append(a.display_name)
        return ", ".join(lines)

    @api.model
    def _parse_intent(self, message):
        """Use OpenAI to parse user message into structured intent JSON."""
        client = self._get_openai_client()
        if not client:
            return {'intent': 'error', 'error': 'Configuration manquante (clé OpenAI)'}

        product_list = self._get_product_list_text()
        # Restrict product list size for prompt efficiency if needed, but here we include it
        system_content = SYSTEM_PROMPT_TEMPLATE + "\n\nLISTE DES PRODUITS DISPONIBLES :\n" + product_list

        try:
            response = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {'role': 'system', 'content': system_content},
                    {'role': 'user', 'content': message},
                ],
                temperature=0,
                max_tokens=1000,
                response_format={ "type": "json_object" }
            )
            raw = response.choices[0].message.content.strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            _logger.warning("OpenAI returned non-JSON: %s", raw)
            return {'intent': 'unknown'}
        except Exception as e:
            _logger.error("OpenAI API error: %s", str(e))
            return {'intent': 'error', 'error': str(e)}

    @api.model
    def _resolve_product(self, product_name):
        """Search for a casa.product by name or article alias."""
        if not product_name:
            return None

        # 1. Search in casa.product names
        Product = self.env['casa.product'].sudo()
        product = Product.search([('name', 'ilike', product_name)], limit=1)
        if product:
            return product

        # 2. Search in company.article aliases
        Article = self.env['company.article'].sudo()
        article = Article.search([
            '|', ('display_name', 'ilike', product_name), ('alias_ids.name', 'ilike', product_name)
        ], limit=1)
        
        if article:
            product = Product.search([('article_id', '=', article.id)], limit=1)
            return product

        return None

    @api.model
    def _normalize_lot(self, lot_str):
        """Remove all non-alphanumeric characters and lowercase for comparison."""
        if not lot_str:
            return ""
        return re.sub(r'[^a-zA-Z0-9]', '', str(lot_str)).lower()

    @api.model
    def _validate_order_line(self, item):
        """Check if Product/Lot combination exists in casa.stock.stock."""
        qty = item.get('qty')
        product_name = item.get('product') or 'Produit inconnu'
        lot_raw = str(item.get('lot', '')).strip() if item.get('lot') else ''

        if not lot_raw or lot_raw.lower() == 'null':
            return f"{qty or ''} {product_name} -> ⚠️ Lot s'il vous plait"

        Stock = self.env['casa.stock.stock'].sudo()
        
        # 1. Try exact match for lot (case-insensitive)
        domain = [('lot', '=ilike', lot_raw), ('quantity', '>', 0)]
        lot_matches = Stock.search(domain)

        # 2. Try normalized match if no exact match
        if not lot_matches:
            lot_norm = self._normalize_lot(lot_raw)
            all_active_stocks = Stock.search([('quantity', '>', 0)])
            lot_matches = all_active_stocks.filtered(lambda s: self._normalize_lot(s.lot) == lot_norm)

        if lot_matches:
            # User wants to ignore product name if lot is correct
            return "Bien"

        # 3. Flexible Lot Match: Check if any lot of the identified product matches as substring
        product = self._resolve_product(product_name)
        if product:
            available_stocks = Stock.search([('product_id', '=', product.id), ('quantity', '>', 0)])
            for s in available_stocks:
                db_lot_norm = self._normalize_lot(s.lot)
                if db_lot_norm and (db_lot_norm in lot_norm or lot_norm in db_lot_norm):
                    return "Bien"
            
            # Si aucun match, on liste les lots disponibles
            if available_stocks:
                lots = sorted(list(set(available_stocks.mapped('lot'))))
                # Try fuzzy matching on lots
                matches = difflib.get_close_matches(lot_raw, lots, n=1, cutoff=0.6)
                if matches:
                    return f"{qty or ''} {product.name} lot {lot_raw} -> Correction Lot: {matches[0]}"
                else:
                    lots_str = ", ".join(lots)
                    return f"{qty or ''} {product.name} lot {lot_raw} -> ⚠️ Lot non trouvé. Disponibles: {lots_str}"
            else:
                return f"{qty or ''} {product.name} lot {lot_raw} -> ⚠️ Pas de stock pour ce produit"

        return f"{qty or ''} {product_name} lot {lot_raw} -> ⚠️ Produit non reconnu"

    @api.model
    def process_message(self, message, sender='unknown'):
        """Main orchestrator for casa_stock correction bot."""
        # 1. Parse intent
        intent_data = self._parse_intent(message)
        intent = intent_data.get('intent', 'unknown')

        if intent == 'error':
            return "Erreur de configuration. Veuillez contacter l'administrateur."
        if intent == 'unknown':
            return False

        if intent == 'stock_order_validation':
            items = intent_data.get('items', [])
            results = []
            has_errors = False
            
            for item in items:
                res = self._validate_order_line(item)
                if "Bien" not in res:
                    has_errors = True
                    results.append(res)
                else:
                    qty = item.get('qty', '')
                    prod = item.get('product', '')
                    lot = item.get('lot', '')
                    results.append(f"{qty} {prod} lot {lot} -> Bien")
            
            final_report = "\n".join(results)
            if has_errors:
                return f"*Correction Casa*\n🔍🔍🔍\n\n{final_report}"
            else:
                return "✅"

        return False
