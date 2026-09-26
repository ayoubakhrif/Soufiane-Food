import codecs

with codecs.open('custom-addons/kal3iya_stock/views/kal3iya_stock_driver_views.xml', 'r', encoding='utf-8') as f:
    content = f.read()

# Add phone to tree
content = content.replace(
    '                <field name="employee_id"/>\n            </tree>',
    '                <field name="employee_id"/>\n                <field name="phone"/>\n            </tree>'
)

# Add phone and password to form
content = content.replace(
    '                            <field name="employee_id"/>\n                        </group>',
    '                            <field name="employee_id"/>\n                            <field name="phone"/>\n                            <field name="password" password="True"/>\n                        </group>'
)

with codecs.open('custom-addons/kal3iya_stock/views/kal3iya_stock_driver_views.xml', 'w', encoding='utf-8') as f:
    f.write(content)
