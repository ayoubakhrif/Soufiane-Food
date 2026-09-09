import os

filepath = 'custom-addons/tanger_med/views/sutra_views.xml'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_form = """<form>
                    <sheet>
                        <group>
                            <field name="ste_id"/>
                            <field name="amount"/>
                        </group>
                    </sheet>
                </form>"""

new_form = """<form>
                    <sheet>
                        <group>
                            <group string="Configuration">
                                <field name="ste_id"/>
                                <field name="amount"/>
                            </group>
                            <group string="Resume Financier SUTRA" style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid #17a2b8;">
                                <field name="amount_unbilled" widget="monetary"/>
                                <field name="amount_unpaid" widget="monetary"/>
                                <div class="oe_inline" style="border-top: 2px solid #ccc; width: 100%; margin-top: 10px; padding-top: 10px; font-weight: bold; font-size: 1.2em;">
                                    <field name="amount_total_debt" widget="monetary" style="color: #dc3545;"/>
                                </div>
                            </group>
                        </group>
                    </sheet>
                </form>"""

if old_form in content:
    content = content.replace(old_form, new_form)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated config form view")
else:
    print("Could not find the old form string")
