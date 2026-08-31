import os

filepath = "custom-addons/generate_bons/report/bon_report_templates.xml"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old_block = """                        <div class="row" style="margin-top: 100px;">
                            <div class="col-6 text-center">
                                <img t-if="doc.company_id.cachet" t-att-src="image_data_uri(doc.company_id.cachet)" style="max-height: 120px; transform: rotate(-3deg);" alt="Cachet"/>
                            </div>
                            <div class="col-2"></div>
                            <div class="col-4">
                                <div class="net-a-payer-header">NET A PAYER</div>
                                <div class="net-a-payer-value">
                                    <span t-field="doc.total_ttc" t-options='{"widget": "float", "precision": 2}'/>
                                </div>
                            </div>
                        </div>"""

new_block = """                        <div class="row" style="margin-top: 50px;">
                            <div class="col-8"></div>
                            <div class="col-4">
                                <div class="net-a-payer-header">NET A PAYER</div>
                                <div class="net-a-payer-value">
                                    <span t-field="doc.total_ttc" t-options='{"widget": "float", "precision": 2}'/>
                                </div>
                            </div>
                        </div>
                        <div class="row" style="margin-top: 30px;">
                            <div class="col-6"></div>
                            <div class="col-6 text-center">
                                <img t-if="doc.company_id.cachet" t-att-src="image_data_uri(doc.company_id.cachet)" style="max-height: 140px; transform: rotate(-3deg);" alt="Cachet"/>
                            </div>
                        </div>"""

content = content.replace(old_block, new_block)
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("pdf structure updated")
