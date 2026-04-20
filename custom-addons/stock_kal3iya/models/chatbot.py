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
- "stock_check" : l'utilisateur veut connaître la quantité d'un produit
- "list_products" : l'utilisateur veut la liste des produits en stock
- "list_garages" : l'utilisateur veut la liste des garages
- "stock_order_validation" : l'utilisateur envoie un message multi-ligne avec des articles, quantités, garages et lots à vérifier.
- "unknown" : tu ne comprends pas la question

LISTE DES PRODUITS DISPONIBLES (Référentiel exact) :
__PRODUCT_LIST__

Format de réponse pour "stock_check", "list_products", "list_garages":
{
  "intent": "stock_check",
  "product": "utilise le nom exact depuis la liste ci-dessus (ou null)",
  "garage": "nom du garage extrait (ou null)",
  "lot": "numéro de lot extrait (ou null)"
}

Format de réponse pour "stock_order_validation":
{
  "intent": "stock_order_validation",
  "items": [
    {"qty": 100, "product": "nom du produit (utilise le nom EXACT de la liste si possible, sinon garde le nom du message)", "garage": "stok X ou saha", "lot": "numéro brute"},
    ...
  ]
}

Exemples :
- "Combien d'amande?" → {"intent": "stock_check", "product": "Amande Douce", "garage": null, "lot": null}
- "100 lwz mkrkb stok 1 lot 123" → {"intent": "stock_order_validation", "items": [{"qty": 100, "product": "lwz mkrkb", "garage": "stok 1", "lot": "123"}]}

Pour le garage individuel (stock_check), normalise :
- "garage 1", "stok 1", "g1" → "garage1"
- "terrasse", "saha" → "terrasse"
"""


class StockKal3iyaChatbot(models.AbstractModel):
    _name = 'stock.kal3iya.chatbot'
    _description = 'Stock Kal3iya Chatbot Engine'

    # -------------------------------------------------------------------------
    # OpenAI Integration
    # -------------------------------------------------------------------------
    @api.model
    def _get_openai_client(self):
        """Get an OpenAI client using the API key from system parameters."""
        # Look for the common OpenAI key used by other whatsapp modules
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
        """Fetch all product names to feed the OpenAI prompt."""
        products = self.env['stock.kal3iya.product'].sudo().search([])
        return ", ".join(products.mapped('name'))

    @api.model
    def _parse_intent(self, message):
        """Use OpenAI to parse user message into structured intent JSON."""
        client = self._get_openai_client()
        if not client:
            return {'intent': 'error', 'error': 'Configuration manquante (clé OpenAI)'}

        product_list = self._get_product_list_text()
        system_content = SYSTEM_PROMPT_TEMPLATE.replace('__PRODUCT_LIST__', product_list)

        try:
            response = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {'role': 'system', 'content': system_content},
                    {'role': 'user', 'content': message},
                ],
                temperature=0,
                max_tokens=1000,
            )
            raw = response.choices[0].message.content.strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            _logger.warning("OpenAI returned non-JSON: %s", raw)
            return {'intent': 'unknown'}
        except Exception as e:
            _logger.error("OpenAI API error: %s", str(e))
            return {'intent': 'error', 'error': str(e)}

    # -------------------------------------------------------------------------
    # Product Resolution
    # -------------------------------------------------------------------------
    @api.model
    def _resolve_product(self, product_name):
        """
        Search for a product by name using ilike.
        Returns dict:
          - {'status': 'found', 'product': recordset}
          - {'status': 'not_found'}
          - {'status': 'ambiguous', 'names': [...]}
        """
        if not product_name:
            return {'status': 'not_found'}

        Product = self.env['stock.kal3iya.product'].sudo()
        products = Product.search([('name', 'ilike', product_name)])

        if len(products) == 0:
            # Try alias table as fallback
            alias = self.env['ai.alias'].sudo().search([
                ('model_name', '=', 'stock.kal3iya.product'),
                ('input_text', '=ilike', product_name),
            ], limit=1)
            if alias:
                product = Product.browse(alias.record_id)
                if product.exists():
                    return {'status': 'found', 'product': product}
            return {'status': 'not_found'}

        if len(products) == 1:
            return {'status': 'found', 'product': products[0]}

        # Multiple matches → ambiguous
        return {
            'status': 'ambiguous',
            'names': products.mapped('name'),
        }

    # -------------------------------------------------------------------------
    # Stock Query
    # -------------------------------------------------------------------------
    @api.model
    def _query_stock(self, product, garage=None, lot=None):
        """
        Query stock.kal3iya.stock for a resolved product.
        Returns total quantity as float.
        """
        Stock = self.env['stock.kal3iya.stock'].sudo()
        domain = [('product_id', '=', product.id)]

        if garage:
            domain.append(('garage', '=', garage))
        if lot:
            domain.append(('lot', '=ilike', lot))

        lines = Stock.search(domain)
        return sum(line.quantity for line in lines)

    # -------------------------------------------------------------------------
    # Response Formatting
    # -------------------------------------------------------------------------
    @api.model
    def _format_stock_response(self, qty):
        """Format quantity into simple French response."""
        # Display as integer if it's a whole number
        if qty == int(qty):
            return f"{int(qty)} colis"
        return f"{qty} colis"

    @api.model
    def _format_ambiguous_response(self, names):
        """Format clarification question for ambiguous products."""
        lines = ["Plusieurs produits correspondent :"]
        for name in names:
            lines.append(f"- {name}")
        lines.append("Lequel souhaitez-vous ?")
        return "\n".join(lines)

    @api.model
    def _list_products_in_stock(self):
        """List all products that currently have stock > 0."""
        Stock = self.env['stock.kal3iya.stock'].sudo()
        lines = Stock.search([('quantity', '>', 0)])
        product_names = sorted(set(lines.mapped('product_id.name')))
        if not product_names:
            return "Aucun produit en stock."
        result = ["Produits en stock :"]
        for name in product_names:
            result.append(f"- {name}")
        return "\n".join(result)

    @api.model
    def _list_garages(self):
        """List all garages that contain stock."""
        Stock = self.env['stock.kal3iya.stock'].sudo()
        lines = Stock.search([('quantity', '>', 0)])
        garage_field = Stock.fields_get(['garage'])['garage']['selection']
        garage_map = dict(garage_field)
        active_garages = sorted(set(lines.mapped('garage')))
        if not active_garages:
            return "Aucun garage avec du stock."
        result = ["Garages avec du stock :"]
        for g in active_garages:
            label = garage_map.get(g, g)
            result.append(f"- {label}")
        return "\n".join(result)

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    @api.model
    def _log_interaction(self, sender, message, response):
        """Log the interaction for audit purposes."""
        try:
            self.env['ai.interaction.log'].sudo().create({
                'source': 'whatsapp',
                'raw_message': message,
                'parsed_payload': '',
                'validation_result': response,
                'user_identifier': sender,
            })
        except Exception as e:
            _logger.warning("Failed to log chatbot interaction: %s", str(e))

    # -------------------------------------------------------------------------
    # Order Validation Logic
    # -------------------------------------------------------------------------
    @api.model
    def _map_garage_name(self, raw_garage):
        """Map flexible garage names to Odoo selection keys."""
        if not raw_garage:
            return False
        
        raw = raw_garage.lower().strip()
        # Flexibilité demandée: "saha", "errasse", "terase" -> terrasse
        if any(x in raw for x in ['saha', 'errasse', 'terase', 'terrasse']):
            return 'terrasse'
        
        # Flexibilité demandée: "stok", "stopk", "stock" + chiffre -> garageN
        match = re.search(r'(stok|stopk|stock|garage|g)\s*(\d+)', raw)
        if match:
            return f'garage{match.group(2)}'
        
        # Fallback search in labels
        Stock = self.env['stock.kal3iya.stock'].sudo()
        selection = Stock.fields_get(['garage'])['garage']['selection']
        for key, label in selection:
            if raw == key.lower() or raw == label.lower():
                return key
        return False

    @api.model
    def _get_garage_label(self, key):
        """Get human readable label for garage key."""
        if not key:
            return "Inconnu"
        Stock = self.env['stock.kal3iya.stock'].sudo()
        selection = dict(Stock.fields_get(['garage'])['garage']['selection'])
        return selection.get(key, key)

    @api.model
    def _validate_order_line(self, item):
        """Perform Lot-First validation strategy for a single line."""
        qty = item.get('qty')
        product_name = item.get('product') or 'Produit inconnu'
        garage_raw = item.get('garage')
        lot_raw = str(item.get('lot', '')).strip() if item.get('lot') else ''

        # 1. Map Garage
        garage_key = self._map_garage_name(garage_raw)
        
        # 2. Check if Lot is specified
        if not lot_raw or lot_raw.lower() == 'null':
            return f"{qty} {product_name} {garage_raw} -> Lot s'il vous plait"

        Stock = self.env['stock.kal3iya.stock'].sudo()

        # ---------------------------------------------------------
        # STRATÉGIE 1 : RECHERCHE PAR LOT (GLOBAL)
        # ---------------------------------------------------------
        # On cherche ce lot partout dans la base (quantité > 0)
        domain = [('lot', '=ilike', lot_raw), ('quantity', '>', 0)]
        lot_matches = Stock.search(domain)

        if lot_matches:
            # Si on a plusieurs produits avec le même lot, on essaie de filtrer par nom
            if len(lot_matches) > 1:
                # Filtrage simple par ressemblance de nom
                best_match = lot_matches.filtered(lambda s: product_name.lower() in s.product_id.name.lower())
                record = best_match[0] if best_match else lot_matches[0]
            else:
                record = lot_matches[0]

            # Vérification du garage
            if record.garage == garage_key:
                return "Bien"
            else:
                correct_garage = self._get_garage_label(record.garage)
                return f"{qty} {record.product_id.name} {garage_raw} lot {lot_raw} -> Correction Garage: {correct_garage}"

        # ---------------------------------------------------------
        # STRATÉGIE 2 : LOT NON TROUVÉ -> RECHERCHE PAR PRODUIT + SIMILARITÉ
        # ---------------------------------------------------------
        # On essaie de résoudre le produit (soit nom exact, soit fuzzy)
        Product = self.env['stock.kal3iya.product'].sudo()
        product = Product.search([('name', '=', product_name)], limit=1)
        if not product:
            res = self._resolve_product(product_name)
            if res['status'] == 'found':
                product = res['product']
            else:
                return f"{qty} {product_name} {garage_raw} lot {lot_raw} -> Lot non trouvé (Produit non reconnu)"

        # Dans le garage cible, quels sont les lots disponibles pour ce produit ?
        if garage_key:
            available_stocks = Stock.search([
                ('product_id', '=', product.id),
                ('garage', '=', garage_key),
                ('quantity', '>', 0)
            ])
            
            if not available_stocks:
                # Chercher si le produit existe AILLEURS pour aider l'utilisateur
                other_stocks = Stock.search([('product_id', '=', product.id), ('quantity', '>', 0)])
                if other_stocks:
                    garages = ", ".join(set(self._get_garage_label(s.garage) for s in other_stocks))
                    return f"{qty} {product.name} {garage_raw} lot {lot_raw} -> Lot non trouvé (Disponible dans : {garages})"
                return f"{qty} {product.name} {garage_raw} lot {lot_raw} -> Pas de stock trouvé"

            all_lots = available_stocks.mapped('lot')
            
            # Recherche de similarité (typo dans le lot)
            matches = difflib.get_close_matches(lot_raw, all_lots, n=1, cutoff=0.6)
            if matches:
                return f"{qty} {product.name} {garage_raw} lot {lot_raw} -> Correction Lot: {matches[0]}"
            else:
                # Lot totalement différent -> Lister tout
                lots_str = ", ".join(all_lots)
                return f"{qty} {product.name} {garage_raw} lot {lot_raw} -> Lots disponibles: {lots_str}"
        return f"{qty} {product.name} {garage_raw} lot {lot_raw} -> Lot non trouvé"

    @api.model
    def _process_order_validation(self, intent_data):
        """Process all items and return a report where every line is commented."""
        items = intent_data.get('items', [])
        results = []
        
        for item in items:
            res = self._validate_order_line(item)
            if res == "Bien":
                # Reconstruct the line for a positive feedback
                qty = item.get('qty', '')
                prod = item.get('product', '')
                gar = item.get('garage', '')
                lot = item.get('lot', '')
                results.append(f"{qty} {prod} {gar} lot {lot} -> Bien")
            else:
                results.append(res)
            
        return "\n".join(results)

    # -------------------------------------------------------------------------
    # Main Orchestrator
    # -------------------------------------------------------------------------
    @api.model
    def process_message(self, message, sender='unknown'):
        """
        Main entry point. Processes a user message and returns a French response.

        Flow: Parse intent (OpenAI) → Resolve product (DB) → Query stock (DB) → Format
        """
        # Group filtering for order validation
        STOCK_GROUP_ID = '120363403203705514@g.us'
        
        # 1. Parse intent via OpenAI
        intent_data = self._parse_intent(message)
        intent = intent_data.get('intent', 'unknown')

        # 2. Handle by intent
        if intent == 'error':
            response = "Erreur de configuration. Veuillez contacter l'administrateur."

        elif intent == 'stock_order_validation':
            # Check Group ID or sender for specific validation
            if sender != STOCK_GROUP_ID and sender != 'unknown': # Allow unknown for test/direct
                 _logger.info("Ignoring order validation from unauthorized sender: %s", sender)
                 return "Désolé, cette fonction est réservée au groupe de gestion de stock."
            
            response = self._process_order_validation(intent_data)

        elif intent == 'list_products':
            response = self._list_products_in_stock()

        elif intent == 'list_garages':
            response = self._list_garages()

        elif intent == 'stock_check':
            product_name = intent_data.get('product')
            if not product_name:
                response = "Veuillez préciser le nom du produit."
            else:
                # Resolve product
                result = self._resolve_product(product_name)

                if result['status'] == 'not_found':
                    response = "Produit introuvable."

                elif result['status'] == 'ambiguous':
                    response = self._format_ambiguous_response(result['names'])

                elif result['status'] == 'found':
                    product = result['product']
                    # Individual check logic: normalise garage
                    garage_raw = intent_data.get('garage')
                    garage = self._map_garage_name(garage_raw) if garage_raw else None
                    lot = intent_data.get('lot')
                    qty = self._query_stock(product, garage=garage, lot=lot)
                    response = self._format_stock_response(qty)
        else:
            # unknown intent
            response = ("Je suis l'assistant stock. Vous pouvez me demander :\n"
                        "- La quantité d'un produit (ex: \"Combien d'amande ?\")\n"
                        "- Analyser une commande multi-ligne\n"
                        "- La liste des produits en stock")

        # 3. Log interaction
        self._log_interaction(sender, message, response)

        return response
