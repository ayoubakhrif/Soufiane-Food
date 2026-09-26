import codecs

with codecs.open('custom-addons/kal3iya_stock/views/kal3iya_stock_driver_views.xml', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('<field name="phone"/>\n', '')
content = content.replace('                            <field name="password" password="True"/>\n', '')

with codecs.open('custom-addons/kal3iya_stock/views/kal3iya_stock_driver_views.xml', 'w', encoding='utf-8') as f:
    f.write(content)
