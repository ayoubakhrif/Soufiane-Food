import os

content = """from odoo import models, api, _
from collections import defaultdict
from datetime import datetime, timedelta

def get_week_label(date_obj):
    if not date_obj:
        return ("Sans Date", "Sans Date")
    start_of_week = date_obj - timedelta(days=date_obj.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    week_str = "Semaine {} (Du {} au {})".format(
        date_obj.isocalendar()[1],
        start_of_week.strftime('%d/%m'),
        end_of_week.strftime('%d/%m')
    )
    # Return a tuple (sort_key, label) so we can sort by start_of_week
    return (start_of_week.strftime('%Y-%m-%d'), week_str)

class TripRecapReport(models.AbstractModel):
    _name = 'report.transport_management.report_trip_recap_template'
    _description = 'Report Trip Recap'

    @api.model
    def _get_report_values(self, docids, data=None):
        trips = self.env['transport.trip'].browse(docids).sorted(key=lambda t: (t.driver_id.name or '', str(t.date) if t.date else ''), reverse=True)
        
        drivers_dict = {}
        global_count = len(trips)
        global_profit = 0.0
        global_charges = 0.0
        global_going = 0.0
        global_returning = 0.0
        
        global_fuel = 0.0
        global_driver = 0.0
        global_adblue = 0.0
        global_mixed = 0.0
        
        global_by_week = defaultdict(lambda: {'count': 0, 'profit': 0.0, 'charges': 0.0, 'fuel': 0.0, 'driver': 0.0, 'adblue': 0.0, 'mixed': 0.0, 'label': ''})
        
        for trip in trips:
            driver = trip.driver_id
            week_key, week_label = get_week_label(trip.date)
            
            if driver not in drivers_dict:
                drivers_dict[driver] = {
                    'driver': driver,
                    'count': 0,
                    'profit': 0.0,
                    'charges': 0.0,
                    'fuel': 0.0,
                    'driver_charge': 0.0,
                    'adblue': 0.0,
                    'mixed': 0.0,
                    'by_week': defaultdict(list)
                }
                
            drivers_dict[driver]['count'] += 1
            drivers_dict[driver]['profit'] += trip.profit
            drivers_dict[driver]['charges'] += trip.total_amount
            drivers_dict[driver]['fuel'] += trip.charge_fuel
            drivers_dict[driver]['driver_charge'] += trip.charge_driver
            drivers_dict[driver]['adblue'] += trip.charge_adblue
            drivers_dict[driver]['mixed'] += trip.charge_mixed
            drivers_dict[driver]['by_week'][week_key].append((week_label, trip))
            
            global_profit += trip.profit
            global_charges += trip.total_amount
            global_going += trip.going_price
            global_returning += trip.returning_price
            
            global_fuel += trip.charge_fuel
            global_driver += trip.charge_driver
            global_adblue += trip.charge_adblue
            global_mixed += trip.charge_mixed
            
            global_by_week[week_key]['label'] = week_label
            global_by_week[week_key]['count'] += 1
            global_by_week[week_key]['profit'] += trip.profit
            global_by_week[week_key]['charges'] += trip.total_amount
            global_by_week[week_key]['fuel'] += trip.charge_fuel
            global_by_week[week_key]['driver'] += trip.charge_driver
            global_by_week[week_key]['adblue'] += trip.charge_adblue
            global_by_week[week_key]['mixed'] += trip.charge_mixed
            
        drivers_list = []
        for driver, d_data in drivers_dict.items():
            weeks_list = []
            for w_key, w_trips_tuples in sorted(d_data['by_week'].items(), key=lambda x: x[0], reverse=True):
                w_label = w_trips_tuples[0][0]
                w_trips = [t[1] for t in w_trips_tuples]
                weeks_list.append({
                    'label': w_label,
                    'trips': w_trips,
                    'count': len(w_trips),
                    'profit': sum(t.profit for t in w_trips),
                    'charges': sum(t.total_amount for t in w_trips),
                    'fuel': sum(t.charge_fuel for t in w_trips),
                    'driver': sum(t.charge_driver for t in w_trips),
                    'adblue': sum(t.charge_adblue for t in w_trips),
                    'mixed': sum(t.charge_mixed for t in w_trips),
                })
            d_data['weeks_list'] = weeks_list
            drivers_list.append(d_data)
            
        drivers_list.sort(key=lambda x: x['driver'].name if x['driver'] else '')
        
        global_weeks_list = []
        for w_key, g_data in sorted(global_by_week.items(), key=lambda x: x[0], reverse=True):
            global_weeks_list.append({
                'label': g_data['label'],
                'count': g_data['count'],
                'profit': g_data['profit'],
                'charges': g_data['charges'],
                'fuel': g_data['fuel'],
                'driver': g_data['driver'],
                'adblue': g_data['adblue'],
                'mixed': g_data['mixed'],
            })
            
        report_date = datetime.now().strftime('%d/%m/%Y %H:%M')

        return {
            'doc_ids': docids,
            'doc_model': 'transport.trip',
            'docs': trips,
            'drivers_list': drivers_list,
            'global_count': global_count,
            'global_profit': global_profit,
            'global_charges': global_charges,
            'global_going': global_going,
            'global_returning': global_returning,
            'global_fuel': global_fuel,
            'global_driver': global_driver,
            'global_adblue': global_adblue,
            'global_mixed': global_mixed,
            'global_days_list': global_weeks_list,  # kept same variable name to avoid changing too much xml
            'report_date': report_date
        }

class TripRemorqueRecapReport(models.AbstractModel):
    _name = 'report.transport_management.report_trip_remorque_recap_template'
    _description = 'Report Trip Remorque Recap'

    @api.model
    def _get_report_values(self, docids, data=None):
        trips = self.env['transport.trip.remorque'].browse(docids).sorted(key=lambda t: (t.driver_remorque_id.name or '', str(t.date) if t.date else ''), reverse=True)
        
        drivers_dict = {}
        global_count = len(trips)
        global_profit = 0.0
        global_charges = 0.0
        global_going = 0.0
        global_returning = 0.0
        
        global_fuel = 0.0
        global_driver = 0.0
        global_adblue = 0.0
        global_mixed = 0.0
        
        global_by_week = defaultdict(lambda: {'count': 0, 'profit': 0.0, 'charges': 0.0, 'fuel': 0.0, 'driver': 0.0, 'adblue': 0.0, 'mixed': 0.0, 'label': ''})
        
        for trip in trips:
            driver = trip.driver_remorque_id
            week_key, week_label = get_week_label(trip.date)
            
            if driver not in drivers_dict:
                drivers_dict[driver] = {
                    'driver': driver,
                    'count': 0,
                    'profit': 0.0,
                    'charges': 0.0,
                    'fuel': 0.0,
                    'driver_charge': 0.0,
                    'adblue': 0.0,
                    'mixed': 0.0,
                    'by_week': defaultdict(list)
                }
                
            drivers_dict[driver]['count'] += 1
            drivers_dict[driver]['profit'] += trip.profit
            drivers_dict[driver]['charges'] += trip.total_amount
            drivers_dict[driver]['fuel'] += trip.charge_fuel
            drivers_dict[driver]['driver_charge'] += trip.charge_driver
            drivers_dict[driver]['adblue'] += trip.charge_adblue
            drivers_dict[driver]['mixed'] += trip.charge_mixed
            drivers_dict[driver]['by_week'][week_key].append((week_label, trip))
            
            global_profit += trip.profit
            global_charges += trip.total_amount
            global_going += trip.going_price
            global_returning += trip.returning_price
            
            global_fuel += trip.charge_fuel
            global_driver += trip.charge_driver
            global_adblue += trip.charge_adblue
            global_mixed += trip.charge_mixed
            
            global_by_week[week_key]['label'] = week_label
            global_by_week[week_key]['count'] += 1
            global_by_week[week_key]['profit'] += trip.profit
            global_by_week[week_key]['charges'] += trip.total_amount
            global_by_week[week_key]['fuel'] += trip.charge_fuel
            global_by_week[week_key]['driver'] += trip.charge_driver
            global_by_week[week_key]['adblue'] += trip.charge_adblue
            global_by_week[week_key]['mixed'] += trip.charge_mixed
            
        drivers_list = []
        for driver, d_data in drivers_dict.items():
            weeks_list = []
            for w_key, w_trips_tuples in sorted(d_data['by_week'].items(), key=lambda x: x[0], reverse=True):
                w_label = w_trips_tuples[0][0]
                w_trips = [t[1] for t in w_trips_tuples]
                weeks_list.append({
                    'label': w_label,
                    'trips': w_trips,
                    'count': len(w_trips),
                    'profit': sum(t.profit for t in w_trips),
                    'charges': sum(t.total_amount for t in w_trips),
                    'fuel': sum(t.charge_fuel for t in w_trips),
                    'driver': sum(t.charge_driver for t in w_trips),
                    'adblue': sum(t.charge_adblue for t in w_trips),
                    'mixed': sum(t.charge_mixed for t in w_trips),
                })
            d_data['weeks_list'] = weeks_list
            drivers_list.append(d_data)
            
        drivers_list.sort(key=lambda x: x['driver'].name if x['driver'] else '')
        
        global_weeks_list = []
        for w_key, g_data in sorted(global_by_week.items(), key=lambda x: x[0], reverse=True):
            global_weeks_list.append({
                'label': g_data['label'],
                'count': g_data['count'],
                'profit': g_data['profit'],
                'charges': g_data['charges'],
                'fuel': g_data['fuel'],
                'driver': g_data['driver'],
                'adblue': g_data['adblue'],
                'mixed': g_data['mixed'],
            })
            
        report_date = datetime.now().strftime('%d/%m/%Y %H:%M')

        return {
            'doc_ids': docids,
            'doc_model': 'transport.trip.remorque',
            'docs': trips,
            'drivers_list': drivers_list,
            'global_count': global_count,
            'global_profit': global_profit,
            'global_charges': global_charges,
            'global_going': global_going,
            'global_returning': global_returning,
            'global_fuel': global_fuel,
            'global_driver': global_driver,
            'global_adblue': global_adblue,
            'global_mixed': global_mixed,
            'global_days_list': global_weeks_list,
            'report_date': report_date
        }
"""
with open('c:/odoo-repos/Soufiane-Food/custom-addons/transport_management/report/transport_trip_recap_parser.py', 'w', encoding='utf-8') as f:
    f.write(content)
