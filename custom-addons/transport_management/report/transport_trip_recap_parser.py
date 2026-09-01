from odoo import models, api, _
from collections import defaultdict
from datetime import datetime

class TripRecapReport(models.AbstractModel):
    _name = 'report.transport_management.report_trip_recap_template'
    _description = 'Report Trip Recap'

    @api.model
    def _get_report_values(self, docids, data=None):
        trips = self.env['transport.trip'].browse(docids).sorted(key=lambda t: (t.driver_id.name or '', t.date or ''))
        
        drivers_dict = {}
        global_count = len(trips)
        global_profit = 0.0
        global_charges = 0.0
        global_going = 0.0
        global_returning = 0.0
        
        global_by_day = defaultdict(lambda: {'count': 0, 'profit': 0.0, 'charges': 0.0})
        
        for trip in trips:
            driver = trip.driver_id
            if driver not in drivers_dict:
                drivers_dict[driver] = {
                    'driver': driver,
                    'count': 0,
                    'profit': 0.0,
                    'charges': 0.0,
                    'by_day': defaultdict(list)
                }
                
            drivers_dict[driver]['count'] += 1
            drivers_dict[driver]['profit'] += trip.profit
            drivers_dict[driver]['charges'] += trip.total_amount
            drivers_dict[driver]['by_day'][trip.date].append(trip)
            
            global_profit += trip.profit
            global_charges += trip.total_amount
            global_going += trip.going_price
            global_returning += trip.returning_price
            
            global_by_day[trip.date]['count'] += 1
            global_by_day[trip.date]['profit'] += trip.profit
            global_by_day[trip.date]['charges'] += trip.total_amount
            
        # Format the dicts into sorted lists for qweb
        drivers_list = []
        for driver, d_data in drivers_dict.items():
            days_list = []
            for date, day_trips in sorted(d_data['by_day'].items(), key=lambda x: str(x[0]) if x[0] else '', reverse=True):
                days_list.append({
                    'date': date,
                    'trips': day_trips,
                    'count': len(day_trips),
                    'profit': sum(t.profit for t in day_trips),
                    'charges': sum(t.total_amount for t in day_trips)
                })
            d_data['days_list'] = days_list
            drivers_list.append(d_data)
            
        drivers_list.sort(key=lambda x: x['driver'].name if x['driver'] else '')
        
        global_days_list = []
        for date, g_data in sorted(global_by_day.items(), key=lambda x: str(x[0]) if x[0] else '', reverse=True):
            global_days_list.append({
                'date': date,
                'count': g_data['count'],
                'profit': g_data['profit'],
                'charges': g_data['charges']
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
            'global_days_list': global_days_list,
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
        
        global_by_day = defaultdict(lambda: {'count': 0, 'profit': 0.0, 'charges': 0.0})
        
        for trip in trips:
            driver = trip.driver_remorque_id
            if driver not in drivers_dict:
                drivers_dict[driver] = {
                    'driver': driver,
                    'count': 0,
                    'profit': 0.0,
                    'charges': 0.0,
                    'by_day': defaultdict(list)
                }
                
            drivers_dict[driver]['count'] += 1
            drivers_dict[driver]['profit'] += trip.profit
            drivers_dict[driver]['charges'] += trip.total_amount
            drivers_dict[driver]['by_day'][trip.date].append(trip)
            
            global_profit += trip.profit
            global_charges += trip.total_amount
            global_going += trip.going_price
            global_returning += trip.returning_price
            
            global_by_day[trip.date]['count'] += 1
            global_by_day[trip.date]['profit'] += trip.profit
            global_by_day[trip.date]['charges'] += trip.total_amount
            
        drivers_list = []
        for driver, d_data in drivers_dict.items():
            days_list = []
            for date, day_trips in sorted(d_data['by_day'].items(), key=lambda x: str(x[0]) if x[0] else '', reverse=True):
                days_list.append({
                    'date': date,
                    'trips': day_trips,
                    'count': len(day_trips),
                    'profit': sum(t.profit for t in day_trips),
                    'charges': sum(t.total_amount for t in day_trips)
                })
            d_data['days_list'] = days_list
            drivers_list.append(d_data)
            
        drivers_list.sort(key=lambda x: x['driver'].name if x['driver'] else '')
        
        global_days_list = []
        for date, g_data in sorted(global_by_day.items(), key=lambda x: str(x[0]) if x[0] else '', reverse=True):
            global_days_list.append({
                'date': date,
                'count': g_data['count'],
                'profit': g_data['profit'],
                'charges': g_data['charges']
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
            'global_days_list': global_days_list,
            'report_date': report_date
        }
