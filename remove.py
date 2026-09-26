import codecs

with codecs.open('custom-addons/kal3iya_stock/views/kal3iya_stock_master_data_views.xml', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('    <!-- Driver Views -->')
end = content.find('    <!-- Soci')

if start != -1 and end != -1:
    new_content = content[:start] + content[end:]
    with codecs.open('custom-addons/kal3iya_stock/views/kal3iya_stock_master_data_views.xml', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Removed successfully')
else:
    print('Not found')
