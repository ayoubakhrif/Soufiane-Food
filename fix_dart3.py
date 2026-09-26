import codecs

filepath = 'gestion_stock_app/lib/screens/bulk_order_screen.dart'
with codecs.open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("Text('Lot: ', ", "Text('Lot: ${stock.lot}', ")
content = content.replace("Text('DUM: ', ", "Text('DUM: ${stock.dum}', ")
content = content.replace("Text('Dispo: ', ", "Text('Dispo: ${stock.quantity}', ")
content = content.replace("orderRef = 'CMD-$date-';", "orderRef = 'CMD-$date-${DateTime.now().millisecondsSinceEpoch}';")

with codecs.open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
