import os

directory = "custom-addons/generate_bons"

for root, dirs, files in os.walk(directory):
    for file in files:
        filepath = os.path.join(root, file)
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            if content.startswith(b'\xef\xbb\xbf'):
                content = content[3:]
                with open(filepath, 'wb') as f:
                    f.write(content)
                print(f"Removed BOM from {filepath}")
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
