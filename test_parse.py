import json

data = r"""{
    "email_preview": "\\n\\n\\nHi Jordan..."
}"""

parsed = json.loads(data)
print("Option 1 (Escaped string in JSON):")
print(repr(parsed['email_preview']))

data2 = """{
    "email_preview": "\\n\\n\\nHi Jordan..."
}"""

parsed2 = json.loads(data2)
print("Option 2 (Raw literal backslashes in JSON string):")
print(repr(parsed2['email_preview']))

data3 = """{
    "email_preview": "\n\n\nHi Jordan..."
}"""
try:
    json.loads(data3)
except Exception as e:
    print("Option 3 Error:", e)

paragraphs = str(parsed['email_preview']).replace('\\n', '\n').split('\n')
print("Option 1 SPLIT:", paragraphs)

paragraphs2 = str(parsed2['email_preview']).replace('\\n', '\n').split('\n')
print("Option 2 SPLIT:", paragraphs2)
