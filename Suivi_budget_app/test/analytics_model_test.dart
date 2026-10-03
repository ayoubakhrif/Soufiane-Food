import 'package:flutter_test/flutter_test.dart';
import 'package:suivi_budget_app/models/analytics_data.dart';

void main() {
  test('AnalyticsData json parsing test', () {
    final mockJson = {
      'period': {
        'name': '2026-09',
        'date_start': '2026-09-25',
        'date_end': '2026-10-24',
        'month_start_day': 25,
        'days_remaining': 21,
        'total_days': 30,
        'days_passed': 9,
      },
      'kpis': {
        'total_daily': 1500.0,
        'total_fixed': 6000.0,
        'total_all': 7500.0,
        'daily_avg_spent': 166.67,
        'daily_advised': 50.0,
        'remaining_balance': 1050.0,
        'max_day': {
          'date': '2026-09-28',
          'day_label': '28/09',
          'amount': 450.0,
        },
        'top_category': {
          'name': 'Alimentation',
          'amount': 800.0,
          'percentage': 53.3,
        },
      },
      'by_category_daily': [
        {
          'id': 1,
          'name': 'Alimentation',
          'amount': 800.0,
          'percentage': 53.3,
          'count': 5,
        },
        {
          'id': 2,
          'name': 'Carburant',
          'amount': 700.0,
          'percentage': 46.7,
          'count': 2,
        },
      ],
      'by_category_all': [
        {
          'name': 'Loyer',
          'amount': 4000.0,
          'percentage': 53.3,
        },
        {
          'name': 'Alimentation',
          'amount': 800.0,
          'percentage': 10.7,
        },
      ],
      'daily_timeline': [
        {
          'date': '2026-09-25',
          'day': 25,
          'day_label': '25/09',
          'amount': 120.0,
        },
        {
          'date': '2026-09-28',
          'day': 28,
          'day_label': '28/09',
          'amount': 450.0,
        },
      ],
      'top_expenses': [
        {
          'id': 42,
          'date': '2026-09-28',
          'amount': 450.0,
          'category_name': 'Alimentation',
          'description': 'Supermarché',
        },
      ],
    };

    final analytics = AnalyticsData.fromJson(mockJson);

    expect(analytics.period.name, '2026-09');
    expect(analytics.period.formattedStartDate, '25/09');
    expect(analytics.period.formattedEndDate, '24/10');
    expect(analytics.kpis.totalDaily, 1500.0);
    expect(analytics.kpis.maxDayLabel, '28/09');
    expect(analytics.kpis.maxDayAmount, 450.0);
    expect(analytics.kpis.topCategoryName, 'Alimentation');
    expect(analytics.byCategoryDaily.length, 2);
    expect(analytics.byCategoryDaily[0].percentage, 53.3);
    expect(analytics.dailyTimeline.length, 2);
    expect(analytics.topExpenses.length, 1);
    expect(analytics.topExpenses[0].amount, 450.0);
  });
}
