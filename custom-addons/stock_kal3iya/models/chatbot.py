import json
import logging

from odoo import models, api

_logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un assistant qui analyse des messages utilisateur liés à la gestion de stock.
Tu dois extraire l'intention et les paramètres de la question.

Réponds UNIQUEMENT en JSON valide, sans aucun texte autour.

Intentions possibles :
- "stock_check" : l'utilisateur veut connaître la quantité d'un produit
- "list_products" : l'utilisateur veut la liste des produits en stock
- "list_garages" : l'utilisateur veut la liste des garages
- "unknown" : tu ne comprends pas la question

Format de réponse :
{
  "intent": "stock_check",
  "product": "nom du produit extrait (ou null)",
  "garage": "nom du garage extrait (ou null)",
  "lot": "numéro de lot extrait (ou null)"
}

Exemples :
- "Combien d'amande?" → {"intent": "stock_check", "product": "amande", "garage": null, "lot": null}
- "Stock amande garage 1" → {"intent": "stock_check", "product": "amande", "garage": "garage1", "lot": null}
- "Liste des produits" → {"intent": "list_products", "product": null, "garage": null, "lot": null}
- "Quels garages?" → {"intent": "list_garages", "product": null, "garage": null, "lot": null}
- "Bonjour" → {"intent": "unknown", "product": null, "garage": null, "lot": null}

Pour le garage, normalise le nom :
- "garage 1", "Garage 1", "g1" → "garage1"
- "garage 2" → "garage2" ... jusqu'à "garage8"
- "terrasse" → "terrasse"
- "fenidek" → "fenidek"
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
        api_key = self.env['ir.config_parameter'].sudo().get_param('stock_kal3iya.openai_api_key')
        if not api_key:
            _logger.error("OpenAI API key not configured (stock_kal3iya.openai_api_key)")
            return None
        try:
            from openai import OpenAI
            return OpenAI(api_key=api_key)
        except ImportError:
            _logger.error("openai Python package is not installed")
            return None

    @api.model
    def _parse_intent(self, message):
        """Use OpenAI to parse user message into structured intent JSON."""
        client = self._get_openai_client()
        if not client:
            return {'intent': 'error', 'error': 'Configuration manquante'}

        try:
            response = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': message},
                ],
                temperature=0,
                max_tokens=200,
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
    # Main Orchestrator
    # -------------------------------------------------------------------------
    @api.model
    def process_message(self, message, sender='unknown'):
        """
        Main entry point. Processes a user message and returns a French response.

        Flow: Parse intent (OpenAI) → Resolve product (DB) → Query stock (DB) → Format
        """
        # 1. Parse intent via OpenAI
        intent_data = self._parse_intent(message)
        intent = intent_data.get('intent', 'unknown')

        # 2. Handle by intent
        if intent == 'error':
            response = "Erreur de configuration. Veuillez contacter l'administrateur."

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
                    garage = intent_data.get('garage')
                    lot = intent_data.get('lot')
                    qty = self._query_stock(product, garage=garage, lot=lot)
                    response = self._format_stock_response(qty)
        else:
            # unknown intent
            response = ("Je suis l'assistant stock. Vous pouvez me demander :\n"
                        "- La quantité d'un produit (ex: \"Combien d'amande ?\")\n"
                        "- La liste des produits en stock\n"
                        "- La liste des garages")

        # 3. Log interaction
        self._log_interaction(sender, message, response)

        return response
