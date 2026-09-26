import codecs
import re

filepath = 'gestion_stock_app/android/settings.gradle.kts'
with codecs.open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'id\("com\.android\.application"\) version ".*?"', 'id("com.android.application") version "8.5.0"', content)

with codecs.open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
