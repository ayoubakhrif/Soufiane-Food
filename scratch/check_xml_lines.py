with open(r"c:\odoo-repos\Soufiane-Food\custom-addons\tresorerie_chq\views\paiement_views.xml", "rb") as f:
    lines = f.readlines()
for i in range(104, 112):
    print(f"Line {i+1}: {repr(lines[i])}")
