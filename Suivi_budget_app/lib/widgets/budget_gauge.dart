import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/dashboard_data.dart';

class BudgetGauge extends StatelessWidget {
  final TotalsInfo totals;
  final PeriodInfo period;

  const BudgetGauge({
    super.key,
    required this.totals,
    required this.period,
  });

  Color _getStatusColor() {
    if (totals.isExceeded) return const Color(0xFFE53935);
    if (totals.percentage >= 85) return const Color(0xFFFF9800);
    return const Color(0xFF43A047);
  }

  @override
  Widget build(BuildContext context) {
    final currencyFormat = NumberFormat('#,##0.00', 'fr_FR');
    final statusColor = _getStatusColor();
    final progress = (totals.budgetTotal > 0)
        ? (totals.spentTotal / totals.budgetTotal).clamp(0.0, 1.0)
        : 0.0;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 15,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Période & Statut
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      totals.isExceeded ? Icons.warning_rounded : Icons.account_balance_wallet_rounded,
                      color: statusColor,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    'Budget de la période',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: Colors.grey.shade800,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${totals.percentage.toStringAsFixed(1)} %',
                  style: TextStyle(
                    color: statusColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // Montant Restant Mis en Avant
          Text(
            'Reste à dépenser',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w500,
              color: Colors.grey.shade600,
            ),
          ),
          const SizedBox(height: 4),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                currencyFormat.format(totals.remainingTotal),
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.w800,
                  color: totals.isExceeded ? const Color(0xFFE53935) : const Color(0xFF1E293B),
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(width: 6),
              const Text(
                'DH',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF64748B),
                ),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Barre de progression
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 10,
              backgroundColor: Colors.grey.shade200,
              valueColor: AlwaysStoppedAnimation<Color>(statusColor),
            ),
          ),

          const SizedBox(height: 16),

          // Détail : Charges Fixes, Sorties Quotidiennes, Total & Objectif
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.push_pin_rounded, size: 15, color: Color(0xFF64748B)),
                        const SizedBox(width: 6),
                        Text(
                          'Charges Fixes Mensuelles',
                          style: TextStyle(fontSize: 12.5, color: Colors.grey.shade700, fontWeight: FontWeight.w500),
                        ),
                      ],
                    ),
                    Text(
                      '${currencyFormat.format(totals.expenseFixedTotal)} DH',
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF334155),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.shopping_bag_outlined, size: 15, color: Color(0xFF64748B)),
                        const SizedBox(width: 6),
                        Text(
                          'Sorties Quotidiennes',
                          style: TextStyle(fontSize: 12.5, color: Colors.grey.shade700, fontWeight: FontWeight.w500),
                        ),
                      ],
                    ),
                    Text(
                      '${currencyFormat.format(totals.expenseDailyTotal)} DH',
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF334155),
                      ),
                    ),
                  ],
                ),
                const Divider(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Total Dépensé', style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
                        Text(
                          '${currencyFormat.format(totals.spentTotal)} DH',
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF0F172A),
                          ),
                        ),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text('Objectif alloué', style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
                        Text(
                          '${currencyFormat.format(totals.budgetTotal)} DH',
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF0F172A),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),

          const Divider(height: 28),

          // Pastille "Rythme conseillé / jour"
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFFF1F5F9),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.lightbulb_outline_rounded,
                  color: Color(0xFF0284C7),
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: RichText(
                    text: TextSpan(
                      style: const TextStyle(fontSize: 12.5, color: Color(0xFF334155)),
                      children: [
                        const TextSpan(text: 'Rythme conseillé : '),
                        TextSpan(
                          text: '${currencyFormat.format(totals.dailyAdvised)} DH / jour',
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF0284C7),
                          ),
                        ),
                        TextSpan(
                          text: ' (${period.daysRemaining} j restants)',
                          style: TextStyle(color: Colors.grey.shade600),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
