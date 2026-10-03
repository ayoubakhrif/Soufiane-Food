import sys
import re

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

# We need to remove the WhatsApp block in api_bulk_exit
# The block starts with "try:\n                driver_name =" and ends with "_logger.error(f\"WhatsApp send error: {str(e)}\")"

pattern = r"            try:\n                driver_name = request\.env\['casa_field\.stock\.driver'\].*?_logger\.error\(f\"WhatsApp send error: \{str\(e\)\}\"\)"

# Replace with nothing, leaving just the return statement
new_content = re.sub(pattern, "", content, flags=re.DOTALL)

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "w", encoding="utf-8") as f:
    f.write(new_content)
print("Removed WhatsApp from api_bulk_exit")
