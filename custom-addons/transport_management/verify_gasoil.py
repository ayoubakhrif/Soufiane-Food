# Verification Script for Gasoil Stock

def verify_gasoil_stock(env):
    Stock = env['gasoil.stock']
    Refill = env['gasoil.refill']
    Sale = env['gasoil.sale']
    
    # 1. Clean existing data (optional, or just create new test data)
    # Refill.search([]).unlink()
    # Sale.search([]).unlink()
    
    print("--- Starting Gasoil Stock Verification ---")
    
    # 2. initial state
    stock = Stock.get_stock()
    stock._compute_stock() # Ensure clean state calculation
    print(f"Initial Stock: {stock.remaining_liters} L")
    
    # 3. Create Refill
    print("Creating Refill: 1000L @ 10 MAD")
    refill = Refill.create({
        'date': '2026-01-20',
        'liters': 1000.0,
        'purchase_price': 10.0
    })
    
    stock.invalidate_cache()
    stock._compute_stock() # Actually this should interpret the auto-trigger not manual call here if implemented
    print(f"Stock after Refill: {stock.remaining_liters} L (Expected: +1000)")
    
    # 4. Create Sale
    print("Creating Sale: 500 MAD @ 12.5 MAD/L")
    sale = Sale.create({
        'date': '2026-01-20',
        'driver': 'Test Driver',
        'client': 'soufiane',
        'amount': 500.0,
        'sale_price': 12.5,
         # purchase price auto-filled/computed
    })
    
    stock.invalidate_cache()
    print(f"Sale Liters: {sale.liters} L (Expected: 40.0)")
    print(f"Stock after Sale: {stock.remaining_liters} L (Expected: 960.0)")

    # 5. Cleanup
    # refill.unlink()
    # sale.unlink()
