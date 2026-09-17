import os

filepaths = [
    'c:/odoo-repos/Soufiane-Food/custom-addons/transport_management/report/transport_trip_recap_report.xml',
    'c:/odoo-repos/Soufiane-Food/custom-addons/transport_management/report/transport_trip_remorque_recap_report.xml'
]

for fp in filepaths:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()

    old_thead = """                                                <th style="width: 14%;">Client</th>
                                                <th style="width: 9%;">Matricule</th>
                                                <th style="width: 8%;">Allée</th>
                                                <th style="width: 8%;">Retour</th>
                                                <th style="width: 9%;">Total Prix</th>
                                                <th style="width: 8%;">Gazoil</th>
                                                <th style="width: 8%;">Dép.</th>
                                                <th style="width: 8%;">AdBlue</th>
                                                <th style="width: 8%;">Mixe</th>
                                                <th style="width: 10%;">Charges</th>
                                                <th style="width: 10%;">Bénéfice</th>"""

    new_thead = """                                                <th style="width: 9%;">Date</th>
                                                <th style="width: 12%;">Client</th>
                                                <th style="width: 8%;">Matricule</th>
                                                <th style="width: 8%;">Allée</th>
                                                <th style="width: 8%;">Retour</th>
                                                <th style="width: 8%;">Total Prix</th>
                                                <th style="width: 7%;">Gazoil</th>
                                                <th style="width: 7%;">Dép.</th>
                                                <th style="width: 7%;">AdBlue</th>
                                                <th style="width: 7%;">Mixe</th>
                                                <th style="width: 9%;">Charges</th>
                                                <th style="width: 10%;">Bénéfice</th>"""
                                                
    content = content.replace(old_thead, new_thead)
    
    old_tbody_start = """                                                    <td><t t-esc="trip.client_id.name"/></td>
                                                    <td><t t-esc="trip.vehicle_id.matricule if trip.vehicle_id else ''"/></td>"""
                                                    
    new_tbody_start = """                                                    <td><t t-esc="trip.date.strftime('%d/%m') if trip.date else ''"/></td>
                                                    <td><t t-esc="trip.client_id.name"/></td>
                                                    <td><t t-esc="trip.vehicle_id.matricule if trip.vehicle_id else ''"/></td>"""

    content = content.replace(old_tbody_start, new_tbody_start)

    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
print('Done!')
