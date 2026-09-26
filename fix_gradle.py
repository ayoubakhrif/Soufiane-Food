import codecs
import re

filepath = 'gestion_stock_app/android/settings.gradle.kts'
with codecs.open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace AGP version
content = re.sub(r'id\("com\.android\.application"\) version ".*?"', 'id("com.android.application") version "8.3.0"', content)
# Replace Kotlin version
content = re.sub(r'id\("org\.jetbrains\.kotlin\.android"\) version ".*?"', 'id("org.jetbrains.kotlin.android") version "1.9.22"', content)

with codecs.open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
