import sys
import logging

def debug_mais_stock(env):
    Product = env['casa.product']
    Stock = env['casa.stock.stock']
    OrderLine = env['casa.stock.order.line']
    
    product = Product.search([('name', 'ilike', 'mais')], limit=1)
    if product:
        print(f"Product found: {product.name} (ID: {product.id})")
        
        print("\n--- STOCK LINES ---")
        stocks = Stock.search([('product_id', '=', product.id)])
        for s in stocks:
            print(f"  Stock: lot='{s.lot}' dum='{s.dum}' cal='{s.calibre}' ville='{s.ville}' frigo='{s.frigo}' ste='{s.ste_id.name}' wt={s.weight} qty={s.quantity} price={s.price}")
            
        print("\n--- ORDER LINES (Last 3) ---")
        lines = OrderLine.search([('product_id', '=', product.id)], order='id desc', limit=3)
        for l in lines:
            print(f"  Order line: qty={l.qty} lot='{l.lot}' dum='{l.dum}' cal='{l.calibre}' ste='{l.ste_id.name}' wt={l.weight} exit price={l.stock_id.price}")
    else:
        print("Product 'mais' not found.")

debug_mais_stock(env)
