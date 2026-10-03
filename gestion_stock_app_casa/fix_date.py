import re

with open("lib/screens/stock_exit_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

# Add _selectedDate to state
content = content.replace(
    "DriverItem? _selectedDriver;",
    "DriverItem? _selectedDriver;\n  DateTime? _selectedDate = DateTime.now();"
)

# Update _submit to use _selectedDate
old_submit_date = "    final date = DateTime.now().toIso8601String().split('T')[0];"
new_submit_date = "    final date = (_selectedDate ?? DateTime.now()).toIso8601String().split('T')[0];"
content = content.replace(old_submit_date, new_submit_date)

# Add DatePicker to UI
old_ui = """                      children: [
                        DropdownButtonFormField<DriverItem>("""
new_ui = """                      children: [
                        InkWell(
                          onTap: () async {
                            final picked = await showDatePicker(
                              context: context,
                              initialDate: _selectedDate ?? DateTime.now(),
                              firstDate: DateTime(2020),
                              lastDate: DateTime(2100),
                            );
                            if (picked != null) {
                              setState(() => _selectedDate = picked);
                            }
                          },
                          child: InputDecorator(
                            decoration: InputDecoration(
                              labelText: 'Date de sortie',
                              prefixIcon: const Icon(Icons.calendar_today),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                            ),
                            child: Text(_selectedDate != null ? _selectedDate!.toIso8601String().split('T')[0] : 'Sélectionner une date'),
                          ),
                        ),
                        const SizedBox(height: 10),
                        DropdownButtonFormField<DriverItem>("""
content = content.replace(old_ui, new_ui)

with open("lib/screens/stock_exit_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)

print("Modified stock_exit_screen.dart")
