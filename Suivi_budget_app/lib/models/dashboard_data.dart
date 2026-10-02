import 'category_model.dart';
import 'expense_model.dart';

class PeriodInfo {
  final String name;
  final String dateStart;
  final String dateEnd;
  final int monthStartDay;
  final int daysRemaining;
  final int totalDays;

  PeriodInfo({
    required this.name,
    required this.dateStart,
    required this.dateEnd,
    required this.monthStartDay,
    required this.daysRemaining,
    required this.totalDays,
  });

  factory PeriodInfo.fromJson(Map<String, dynamic> json) {
    return PeriodInfo(
      name: json['name']?.toString() ?? '',
      dateStart: json['date_start']?.toString() ?? '',
      dateEnd: json['date_end']?.toString() ?? '',
      monthStartDay: (json['month_start_day'] is num) ? (json['month_start_day'] as num).toInt() : 1,
      daysRemaining: (json['days_remaining'] is num) ? (json['days_remaining'] as num).toInt() : 1,
      totalDays: (json['total_days'] is num) ? (json['total_days'] as num).toInt() : 30,
    );
  }
}

class TotalsInfo {
  final double budgetTotal;
  final double spentTotal;
  final double remainingTotal;
  final double dailyAdvised;
  final double percentage;
  final bool isExceeded;

  TotalsInfo({
    required this.budgetTotal,
    required this.spentTotal,
    required this.remainingTotal,
    required this.dailyAdvised,
    required this.percentage,
    required this.isExceeded,
  });

  factory TotalsInfo.fromJson(Map<String, dynamic> json) {
    return TotalsInfo(
      budgetTotal: (json['budget_total'] is num) ? (json['budget_total'] as num).toDouble() : 0.0,
      spentTotal: (json['spent_total'] is num) ? (json['spent_total'] as num).toDouble() : 0.0,
      remainingTotal: (json['remaining_total'] is num) ? (json['remaining_total'] as num).toDouble() : 0.0,
      dailyAdvised: (json['daily_advised'] is num) ? (json['daily_advised'] as num).toDouble() : 0.0,
      percentage: (json['percentage'] is num) ? (json['percentage'] as num).toDouble() : 0.0,
      isExceeded: json['is_exceeded'] == true,
    );
  }
}

class DashboardData {
  final PeriodInfo period;
  final TotalsInfo totals;
  final List<CategoryModel> categories;
  final List<ExpenseModel> recentExpenses;

  DashboardData({
    required this.period,
    required this.totals,
    required this.categories,
    required this.recentExpenses,
  });

  factory DashboardData.fromJson(Map<String, dynamic> json) {
    final periodJson = json['period'] as Map<String, dynamic>? ?? {};
    final totalsJson = json['totals'] as Map<String, dynamic>? ?? {};
    final categoriesList = (json['categories'] as List<dynamic>? ?? [])
        .map((c) => CategoryModel.fromJson(c as Map<String, dynamic>))
        .toList();
    final recentList = (json['recent_expenses'] as List<dynamic>? ?? [])
        .map((e) => ExpenseModel.fromJson(e as Map<String, dynamic>))
        .toList();

    return DashboardData(
      period: PeriodInfo.fromJson(periodJson),
      totals: TotalsInfo.fromJson(totalsJson),
      categories: categoriesList,
      recentExpenses: recentList,
    );
  }
}
