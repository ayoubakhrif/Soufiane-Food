import 'dashboard_data.dart';

class AnalyticsKpis {
  final double totalDaily;
  final double totalFixed;
  final double totalAll;
  final double dailyAvgSpent;
  final double dailyAdvised;
  final double remainingBalance;
  final String maxDayLabel;
  final double maxDayAmount;
  final String topCategoryName;
  final double topCategoryPercentage;
  final double topCategoryAmount;

  AnalyticsKpis({
    required this.totalDaily,
    required this.totalFixed,
    required this.totalAll,
    required this.dailyAvgSpent,
    required this.dailyAdvised,
    required this.remainingBalance,
    required this.maxDayLabel,
    required this.maxDayAmount,
    required this.topCategoryName,
    required this.topCategoryPercentage,
    required this.topCategoryAmount,
  });

  factory AnalyticsKpis.fromJson(Map<String, dynamic> json) {
    final maxDay = json['max_day'] as Map<String, dynamic>? ?? {};
    final topCat = json['top_category'] as Map<String, dynamic>? ?? {};

    return AnalyticsKpis(
      totalDaily: (json['total_daily'] as num?)?.toDouble() ?? 0.0,
      totalFixed: (json['total_fixed'] as num?)?.toDouble() ?? 0.0,
      totalAll: (json['total_all'] as num?)?.toDouble() ?? 0.0,
      dailyAvgSpent: (json['daily_avg_spent'] as num?)?.toDouble() ?? 0.0,
      dailyAdvised: (json['daily_advised'] as num?)?.toDouble() ?? 0.0,
      remainingBalance: (json['remaining_balance'] as num?)?.toDouble() ?? 0.0,
      maxDayLabel: maxDay['day_label']?.toString() ?? maxDay['date']?.toString() ?? '-',
      maxDayAmount: (maxDay['amount'] as num?)?.toDouble() ?? 0.0,
      topCategoryName: topCat['name']?.toString() ?? 'Aucune',
      topCategoryPercentage: (topCat['percentage'] as num?)?.toDouble() ?? 0.0,
      topCategoryAmount: (topCat['amount'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class CategoryAnalyticsItem {
  final int? id;
  final String name;
  final double amount;
  final double percentage;
  final int count;

  CategoryAnalyticsItem({
    this.id,
    required this.name,
    required this.amount,
    required this.percentage,
    this.count = 0,
  });

  factory CategoryAnalyticsItem.fromJson(Map<String, dynamic> json) {
    return CategoryAnalyticsItem(
      id: json['id'] as int?,
      name: json['name']?.toString() ?? 'Autre',
      amount: (json['amount'] as num?)?.toDouble() ?? 0.0,
      percentage: (json['percentage'] as num?)?.toDouble() ?? 0.0,
      count: json['count'] as int? ?? 0,
    );
  }
}

class DailyTimelineItem {
  final String date;
  final int day;
  final String dayLabel;
  final double amount;

  DailyTimelineItem({
    required this.date,
    required this.day,
    required this.dayLabel,
    required this.amount,
  });

  factory DailyTimelineItem.fromJson(Map<String, dynamic> json) {
    return DailyTimelineItem(
      date: json['date']?.toString() ?? '',
      day: json['day'] as int? ?? 0,
      dayLabel: json['day_label']?.toString() ?? '',
      amount: (json['amount'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class TopExpenseItem {
  final int id;
  final String date;
  final double amount;
  final String categoryName;
  final String description;

  TopExpenseItem({
    required this.id,
    required this.date,
    required this.amount,
    required this.categoryName,
    required this.description,
  });

  factory TopExpenseItem.fromJson(Map<String, dynamic> json) {
    return TopExpenseItem(
      id: json['id'] as int? ?? 0,
      date: json['date']?.toString() ?? '',
      amount: (json['amount'] as num?)?.toDouble() ?? 0.0,
      categoryName: json['category_name']?.toString() ?? 'Autre',
      description: json['description']?.toString() ?? '',
    );
  }
}

class AnalyticsData {
  final PeriodInfo period;
  final AnalyticsKpis kpis;
  final List<CategoryAnalyticsItem> byCategoryDaily;
  final List<CategoryAnalyticsItem> byCategoryAll;
  final List<DailyTimelineItem> dailyTimeline;
  final List<TopExpenseItem> topExpenses;

  AnalyticsData({
    required this.period,
    required this.kpis,
    required this.byCategoryDaily,
    required this.byCategoryAll,
    required this.dailyTimeline,
    required this.topExpenses,
  });

  factory AnalyticsData.fromJson(Map<String, dynamic> json) {
    final periodJson = json['period'] as Map<String, dynamic>? ?? {};
    final kpisJson = json['kpis'] as Map<String, dynamic>? ?? {};

    final catDailyList = (json['by_category_daily'] as List<dynamic>? ?? [])
        .map((e) => CategoryAnalyticsItem.fromJson(e as Map<String, dynamic>))
        .toList();

    final catAllList = (json['by_category_all'] as List<dynamic>? ?? [])
        .map((e) => CategoryAnalyticsItem.fromJson(e as Map<String, dynamic>))
        .toList();

    final timelineList = (json['daily_timeline'] as List<dynamic>? ?? [])
        .map((e) => DailyTimelineItem.fromJson(e as Map<String, dynamic>))
        .toList();

    final topList = (json['top_expenses'] as List<dynamic>? ?? [])
        .map((e) => TopExpenseItem.fromJson(e as Map<String, dynamic>))
        .toList();

    return AnalyticsData(
      period: PeriodInfo.fromJson(periodJson),
      kpis: AnalyticsKpis.fromJson(kpisJson),
      byCategoryDaily: catDailyList,
      byCategoryAll: catAllList,
      dailyTimeline: timelineList,
      topExpenses: topList,
    );
  }
}
