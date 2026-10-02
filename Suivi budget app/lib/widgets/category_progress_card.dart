import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/category_model.dart';

class CategoryProgressCard extends StatelessWidget {
  final CategoryModel category;

  const CategoryProgressCard({
    super.key,
    required this.category,
  });

  IconData _getCategoryIcon(String name) {
    final lower = name.toLowerCase();
    if (lower.contains('alim') || lower.contains('repas') || lower.contains('nourrit') || lower.contains('march')) {
      return Icons.restaurant_rounded;
    }
    if (lower.contains('carbur') || lower.contains('gazoil') || lower.contains('transp') || lower.contains('taxi')) {
      return Icons.directions_car_rounded;
    }
    if (lower.contains('maison') || lower.contains('loyer') || lower.contains('eau') || lower.contains('elec')) {
      return Icons.home_rounded;
    }
    if (lower.contains('sant') || lower.contains('med') || lower.contains('pharm')) {
      return Icons.medical_services_rounded;
    }
    if (lower.contains('loisir') || lower.contains('sorti') || lower.contains('caf')) {
      return Icons.local_cafe_rounded;
    }
    if (lower.contains('vetement') || lower.contains('habit') || lower.contains('shop')) {
      return Icons.shopping_bag_rounded;
    }
    return Icons.category_rounded;
  }

  Color _getProgressColor() {
    if (!category.hasObjective) return const Color(0xFF64748B);
    if (category.isExceeded) return const Color(0xFFE53935);
    if (category.percentage >= 85) return const Color(0xFFFF9800);
    return const Color(0xFF10B981);
  }

  @override
  Widget build(BuildContext context) {
    final currencyFormat = NumberFormat('#,##0.00', 'fr_FR');
    final progressColor = _getProgressColor();
    final progress = category.hasObjective && category.limit > 0
        ? (category.spent / category.limit).clamp(0.0, 1.0)
        : 0.0;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey.shade100),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.02),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: progressColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  _getCategoryIcon(category.name),
                  color: progressColor,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      category.name,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF1E293B),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      category.hasObjective
                          ? 'Dépensé : ${currencyFormat.format(category.spent)} / ${currencyFormat.format(category.limit)} DH'
                          : 'Dépensé : ${currencyFormat.format(category.spent)} DH',
                      style: TextStyle(
                        fontSize: 12.5,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  ],
                ),
              ),
              if (category.hasObjective)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      category.isExceeded ? 'Dépassé' : 'Reste',
                      style: TextStyle(
                        fontSize: 11,
                        color: category.isExceeded ? const Color(0xFFE53935) : Colors.grey.shade500,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    Text(
                      '${currencyFormat.format(category.remaining.abs())} DH',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: progressColor,
                      ),
                    ),
                  ],
                ),
            ],
          ),

          if (category.hasObjective) ...[
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 6,
                backgroundColor: Colors.grey.shade100,
                valueColor: AlwaysStoppedAnimation<Color>(progressColor),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
