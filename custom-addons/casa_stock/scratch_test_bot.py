import os
import sys

# Add Odoo paths (placeholder for actual environment)
# This script is intended to be run via 'odoo-bin shell'

def test_chatbot(env):
    Chatbot = env['casa.stock.chatbot']
    
    print("--- Testing Product Resolution ---")
    # Test case: resolve by direct name
    p = Chatbot._resolve_product("Amande")
    print(f"Amande -> {p.name if p else 'NOT FOUND'}")
    
    # Test case: resolve by alias (if exists)
    # Let's find an alias first to test
    alias = env['company.article.alias'].search([], limit=1)
    if alias:
        p2 = Chatbot._resolve_product(alias.name)
        print(f"Alias '{alias.name}' -> {p2.name if p2 else 'NOT FOUND (Check if linked to Casa Product)'}")

    print("\n--- Testing Lot Normalization ---")
    print(f"Lot '225-B/Mp-07' -> {Chatbot._normalize_lot('225-B/Mp-07')}")

    print("\n--- Testing Chatbot Process (Mock Intent) ---")
    # Mocking what OpenAI would return
    mock_intent = {
        'intent': 'stock_order_validation',
        'items': [
            {'qty': 10, 'product': 'Amande', 'lot': 'LOT123'}, # Assume LOT123 doesn't exist
            {'qty': 5, 'product': 'Inconnu', 'lot': 'NONE'}
        ]
    }
    
    # Since we can't easily run the real process_message (OpenAI skip), we test the internal validation
    for item in mock_intent['items']:
        res = Chatbot._validate_order_line(item)
        print(f"Item {item} -> {res}")

if __name__ == "__main__":
    # This part depends on how you run it, e.g. python odoo-bin shell < this_script
    print("Run this script inside Odoo shell.")
