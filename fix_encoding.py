import os
import codecs

for filename in ['custom-addons/tanger_med/models/sutra.py', 'custom-addons/tanger_med/models/__init__.py', 'custom-addons/tanger_med/models/tanger_med_entry.py']:
    try:
        with open(filename, 'rb') as f:
            raw = f.read()
        
        # Check if it's UTF-16 LE (starts with BOM or has null bytes)
        if raw.startswith(codecs.BOM_UTF16_LE) or b'\x00' in raw:
            text = raw.decode('utf-16-le')
            if text.startswith('\ufeff'):
                text = text[1:]
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"Fixed encoding for {filename}")
        else:
            print(f"No fix needed for {filename}")
    except Exception as e:
        print(f"Error checking {filename}: {e}")
