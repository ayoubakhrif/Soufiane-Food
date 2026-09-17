import os

filepaths = [
    'c:/odoo-repos/Soufiane-Food/custom-addons/transport_management/report/transport_trip_recap_report.xml',
    'c:/odoo-repos/Soufiane-Food/custom-addons/transport_management/report/transport_trip_remorque_recap_report.xml'
]

for fp in filepaths:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update days_list to weeks_list
    content = content.replace("t-foreach=\"d_data['days_list']\"", "t-foreach=\"d_data['weeks_list']\"")

    # 2. Update day-header to use label
    old_day_header = """<div class="day-header">
                                        Date : <t t-if="day_data['date']"><t t-esc="day_data['date'].strftime('%d/%m/%Y')"/></t><t t-else="">Non définie</t> 
                                        - <t t-esc="day_data['count']"/> voyage(s) (Bénéfice: <t t-esc="'{:,.2f}'.format(day_data['profit']).replace(',', ' ')"/>)
                                    </div>"""
                                    
    new_day_header = """<div class="day-header">
                                        <t t-esc="day_data['label']"/> 
                                        - <t t-esc="day_data['count']"/> voyage(s) (Bénéfice: <t t-esc="'{:,.2f}'.format(day_data['profit']).replace(',', ' ')"/> DH)
                                    </div>"""
    content = content.replace(old_day_header, new_day_header)
    
    # Also another possible variant of day_header:
    old_day_header2 = """Date : <t t-if="day_data['date']"><t t-esc="day_data['date'].strftime('%d/%m/%Y')"/></t><t t-else="">Non définie</t>"""
    new_day_header2 = """<t t-esc="day_data['label']"/>"""
    content = content.replace(old_day_header2, new_day_header2)

    # 3. Update global summary header title
    content = content.replace("Récapitulatif par Jour", "Récapitulatif par Semaine")
    
    # 4. Update global summary Date column header
    content = content.replace('<th style="width: 16%;">Date</th>', '<th style="width: 16%;">Semaine</th>')
    content = content.replace('<th style="width: 14%;">Date</th>', '<th style="width: 14%;">Semaine</th>')

    # 5. Update global summary date rendering
    old_g_day_date = """<td><t t-if="g_day['date']"><t t-esc="g_day['date'].strftime('%d/%m/%Y')"/></t></td>"""
    new_g_day_date = """<td><t t-esc="g_day['label']"/></td>"""
    content = content.replace(old_g_day_date, new_g_day_date)
    
    # Add Matricule column
    old_client_th = '<th style="width: 14%;">Client</th>'
    new_client_th = '<th style="width: 14%;">Client</th>\n                                                <th style="width: 9%;">Matricule</th>'
    
    content = content.replace(old_client_th, new_client_th)
    
    old_client_td = '<td><t t-esc="trip.client_id.name"/></td>'
    new_client_td = '<td><t t-esc="trip.client_id.name"/></td>\n                                                    <td><t t-esc="trip.vehicle_id.name if trip.vehicle_id else \'\'"/></td>'
    
    content = content.replace(old_client_td, new_client_td)
    
    # Adjust other widths to make space for matricule (9%)
    content = content.replace('<th style="width: 11%;">Total Prix</th>', '<th style="width: 9%;">Total Prix</th>')
    content = content.replace('<th style="width: 10%;">Charges</th>', '<th style="width: 9%;">Charges</th>')
    content = content.replace('<th style="width: 10%;">Allée</th>', '<th style="width: 8%;">Allée</th>')
    content = content.replace('<th style="width: 10%;">Retour</th>', '<th style="width: 8%;">Retour</th>')

    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
