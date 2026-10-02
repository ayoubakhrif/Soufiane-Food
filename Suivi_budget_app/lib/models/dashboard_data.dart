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
  final double incomeTotal;
  final double incomeFixed;
  final double incomeDaily;
  final double budgetTotal;
  final double spentTotal;
  final double expenseFixedTotal;
  final double expenseDailyTotal;
  final double remainingTotal;
  final double dailyAdvised;
  final double percentage;
  final bool isExceeded;

  TotalsInfo({
    required this.incomeTotal,
    required this.incomeFixed,
    required this.incomeDaily,
    required this.budgetTotal,
    required this.spentTotal,
    required this.expenseFixedTotal,
    required this.expenseDailyTotal,
    required this.remainingTotal,
    required this.dailyAdvised,
    required this.percentage,
    required this.isExceeded,
  });

  factory TotalsInfo.fromJson(Map<String, dynamic> json) {
    return TotalsInfo(
      incomeTotal: (json['income_total'] is num) ? (json['income_total'] as num).toDouble() : 0.0,
      incomeFixed: (json['income_fixed'] is num) ? (json['income_fixed'] as num).toDouble() : 0.0,
      incomeDaily: (json['income_daily'] is num) ? (json['income_daily'] as num).toDouble() : 0.0,
      budgetTotal: (json['budget_total'] is num) ? (json['budget_total'] as num).toDouble() : 0.0,
      spentTotal: (json['spent_total'] is num) ? (json['spent_total'] as num).toDouble() : 0.0,
      expenseFixedTotal: (json['expense_fixed_total'] is num) ? (json['expense_fixed_total'] as num).toDouble() : 0.0,
      expenseDailyTotal: (json['expense_daily_total'] is num) ? (json['expense_daily_total'] as num).toDouble() : 0.0,
      remainingTotal: (json['remaining_total'] is num) ? (json['remaining_total'] as num).toDouble() : 0.0,
      dailyAdvised: (json['daily_advised'] is num) ? (json['daily_advised'] as num).toDouble() : 0.0,
      percentage: (json['percentage'] is num) ? (json['percentage'] as num).toDouble() : 0.0,
      isExceeded: json['is_exceeded'] == true,
    );
  }
}

class MonthlyExpenseModel {
  final int id;
  final String name;
  final String category;
  final double amount;
  final String description;

  MonthlyExpenseModel({
    required this.id,
    required this.name,
    required this.category,
    required this.amount,
    required this.description,
  });

  factory MonthlyExpenseModel.fromJson(Map<String, dynamic> json) {
    return MonthlyExpenseModel(
      id: json['id'] is int ? json['id'] : int.tryParse(json['id'].toString()) ?? 0,
      name: json['name']?.toString() ?? '',
      category: json['category']?.toString() ?? '',
      amount: (json['amount'] is num) ? (json['amount'] as num).toDouble() : 0.0,
      description: json['description']?.toString() ?? '',
    );
  }
}

class DashboardData {
  final PeriodInfo period;
  final TotalsInfo totals;
  final List<CategoryModel> categories;
  final List<ExpenseModel> recentExpenses;
  final List<MonthlyExpenseModel> monthlyExpenses;

  DashboardData({
    required this.period,
    required this.totals,
    required this.categories,
    required this.recentExpenses,
    required this.monthlyExpenses,
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
    final monthlyList = (json['monthly_expenses'] as List<dynamic>? ?? [])
        .map((m) => MonthlyExpenseModel.fromJson(m as Map<String, dynamic>))
        .toList();

    return DashboardData(
      period: PeriodInfo.fromJson(periodJson),
      totals: TotalsInfo.fromJson(totalsJson),
      categories: categoriesList,
      recentExpenses: recentList,
      monthlyExpenses: monthlyList,
    );
  }
}
