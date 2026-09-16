import os

filepaths = [
    'c:/odoo-repos/Soufiane-Food/custom-addons/transport_management/report/transport_trip_recap_report.xml',
    'c:/odoo-repos/Soufiane-Food/custom-addons/transport_management/report/transport_trip_remorque_recap_report.xml'
]

for fp in filepaths:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add headers to the data-table
    old_data_thead = '''                                            <tr>
                                                <th style="width: 15%;">Client</th>
                                                <th style="width: 15%;">Type</th>
                                                <th style="width: 15%;">Allée</th>
                                                <th style="width: 15%;">Retour</th>
                                                <th style="width: 15%;">Total Prix</th>
                                                <th style="width: 15%;">Charges</th>
                                                <th style="width: 10%;">Bénéfice</th>
                                            </tr>'''
                                            
    new_data_thead = '''                                            <tr>
                                                <th style="width: 12%;">Client</th>
                                                <th style="width: 10%;">Type</th>
                                                <th style="width: 8%;">Allée</th>
                                                <th style="width: 8%;">Retour</th>
                                                <th style="width: 9%;">Total Prix</th>
                                                <th style="width: 8%;">Gazoil</th>
                                                <th style="width: 8%;">Dép.</th>
                                                <th style="width: 8%;">AdBlue</th>
                                                <th style="width: 8%;">Mixe</th>
                                                <th style="width: 11%;">Charges</th>
                                                <th style="width: 10%;">Bénéfice</th>
                                            </tr>'''
                                            
    if 'remorque' in fp:
        old_data_thead = old_data_thead.replace('<th>Type</th>', '<th>Destination</th>')
        new_data_thead = new_data_thead.replace('<th>Type</th>', '<th>Destination</th>')

    content = content.replace(old_data_thead, new_data_thead)

    # 2. Add columns to the data-table rows
    # <td class="amount-cell"><t t-esc="'{:,.2f}'.format(trip.total_price).replace(',', ' ')"/></td>
    total_prix_td = '''<td class="amount-cell"><t t-esc="'{:,.2f}'.format(trip.total_price).replace(',', ' ')"/></td>'''
    new_tds = '''<td class="amount-cell"><t t-esc="'{:,.2f}'.format(trip.charge_fuel).replace(',', ' ')"/></td>
                                                    <td class="amount-cell"><t t-esc="'{:,.2f}'.format(trip.charge_driver).replace(',', ' ')"/></td>
                                                    <td class="amount-cell"><t t-esc="'{:,.2f}'.format(trip.charge_adblue).replace(',', ' ')"/></td>
                                                    <td class="amount-cell"><t t-esc="'{:,.2f}'.format(trip.charge_mixed).replace(',', ' ')"/></td>'''
    content = content.replace(total_prix_td, total_prix_td + '\n                                                    ' + new_tds)

    # 3. Add to daily summary table
    old_summary_th = '''                                    <th style="width: 25%;">Date</th>
                                    <th style="width: 25%;">Nbr. Voyages'''
                                    
    new_summary_th = '''                                    <th style="width: 16%;">Date</th>
                                    <th style="width: 12%;">Nbr. Voyages'''
    
    if 'remorque' in fp:
        old_summary_th += ' Remorque</th>'
        new_summary_th += ' Remorque</th>'
    else:
        old_summary_th += '</th>'
        new_summary_th += '</th>'
        
    old_summary_th += '''
                                    <th style="width: 25%;">Charges Totales</th>
                                    <th style="width: 25%;">Bénéfice Total</th>'''
                                    
    new_summary_th += '''
                                    <th style="width: 10%;">Gazoil</th>
                                    <th style="width: 10%;">Dép.</th>
                                    <th style="width: 10%;">AdBlue</th>
                                    <th style="width: 10%;">Mixe</th>
                                    <th style="width: 16%;">Tot. Charges</th>
                                    <th style="width: 16%;">Bénéfice Total</th>'''
                                    
    content = content.replace(old_summary_th, new_summary_th)

    # 3b. Daily summary rows
    count_td = '''<td><t t-esc="g_day['count']"/></td>'''
    new_count_tds = '''<td><t t-esc="g_day['count']"/></td>
                                        <td class="amount-cell"><t t-esc="'{:,.2f}'.format(g_day['fuel']).replace(',', ' ')"/></td>
                                        <td class="amount-cell"><t t-esc="'{:,.2f}'.format(g_day['driver']).replace(',', ' ')"/></td>
                                        <td class="amount-cell"><t t-esc="'{:,.2f}'.format(g_day['adblue']).replace(',', ' ')"/></td>
                                        <td class="amount-cell"><t t-esc="'{:,.2f}'.format(g_day['mixed']).replace(',', ' ')"/></td>'''
    content = content.replace(count_td, new_count_tds)

    # 4. Global summary table
    old_global_th = '''                                    <th style="width: 20%;">Total Voyages'''
    new_global_th = '''                                    <th style="width: 12%;">Total Voyages'''
    
    if 'remorque' in fp:
        old_global_th += ' Remorque</th>'
        new_global_th += ' Remorque</th>'
    else:
        old_global_th += '</th>'
        new_global_th += '</th>'
        
    old_global_th += '''
                                    <th style="width: 20%;">Total Allées</th>
                                    <th style="width: 20%;">Total Retours</th>
                                    <th style="width: 20%;">Total Charges</th>
                                    <th style="width: 20%;">Bénéfice Global</th>'''
                                    
    new_global_th += '''
                                    <th style="width: 12%;">Tot. Allées</th>
                                    <th style="width: 12%;">Tot. Retours</th>
                                    <th style="width: 10%;">Tot. Gazoil</th>
                                    <th style="width: 10%;">Tot. Dép.</th>
                                    <th style="width: 10%;">Tot. AdBlue</th>
                                    <th style="width: 10%;">Tot. Mixe</th>
                                    <th style="width: 12%;">Tot. Charges</th>
                                    <th style="width: 12%;">Bénéf. Global</th>'''
                                    
    content = content.replace(old_global_th, new_global_th)

    # 4b. Global summary rows
    returning_td = '''<td class="amount-cell"><t t-esc="'{:,.2f}'.format(global_returning).replace(',', ' ')"/> DH</td>'''
    new_returning_tds = '''<td class="amount-cell"><t t-esc="'{:,.2f}'.format(global_returning).replace(',', ' ')"/> DH</td>
                                    <td class="amount-cell"><t t-esc="'{:,.2f}'.format(global_fuel).replace(',', ' ')"/> DH</td>
                                    <td class="amount-cell"><t t-esc="'{:,.2f}'.format(global_driver).replace(',', ' ')"/> DH</td>
                                    <td class="amount-cell"><t t-esc="'{:,.2f}'.format(global_adblue).replace(',', ' ')"/> DH</td>
                                    <td class="amount-cell"><t t-esc="'{:,.2f}'.format(global_mixed).replace(',', ' ')"/> DH</td>'''
    content = content.replace(returning_td, new_returning_tds)

    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)

print("Modification terminee.")
