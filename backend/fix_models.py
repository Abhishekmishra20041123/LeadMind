import os, glob

files_to_fix = glob.glob('**/*.py', recursive=True)
for filepath in files_to_fix:
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if 'minimax-m2.5:cloud' in content or 'minimax-m2.5:cloud' in content:
            content = content.replace('', '')
            content = content.replace("", "")
            content = content.replace("OllamaWrapper()", "OllamaWrapper()")
            content = content.replace('OllamaWrapper()', 'OllamaWrapper()')
            
            content = content.replace('', '')
            content = content.replace("", "")
            content = content.replace("OllamaWrapper()", "OllamaWrapper()")
            content = content.replace('OllamaWrapper()', 'OllamaWrapper()')
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print('Fixed ' + filepath)
    except Exception as e:
        print('Error with ' + filepath + ': ' + str(e))
