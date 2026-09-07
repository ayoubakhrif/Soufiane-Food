import os
import codecs

for filename in ['custom-addons/tanger_med/views/sutra_views.xml', 'custom-addons/tanger_med/security/ir.model.access.csv', 'custom-addons/tanger_med/__manifest__.py']:
    try:
        with open(filename, 'rb') as f:
            raw = f.read()
        
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
