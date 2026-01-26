# Check kal3iyasortie data
model = env['kal3iyasortie']
records = model.search([], limit=5)
print(f"Total Records found: {model.search_count([])}")
for r in records:
    print(f"ID: {r.id}, Client: {r.client_id.name} ({r.client_id.id}), Week: '{r.week}', Date: {r.date_exit}")
