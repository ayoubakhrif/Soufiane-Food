import codecs

filepath = 'gestion_stock_app/lib/screens/bulk_order_screen.dart'
with codecs.open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("Text('Erreur de chargement: ')", "Text('Erreur de chargement: $e')")
content = content.replace("Text('Erreur: ')", "Text('Erreur: $e')")

with codecs.open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
