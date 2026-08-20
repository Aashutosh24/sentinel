import os

d = 'c:/Users/olive/Downloads/sentinel-ai-llm-copilot-handoff (2)/kratos/src'
reps = {
    'â€”': '—',
    'Â·': '·',
    'â€™': '’',
    'â€œ': '“',
    'â€': '”',
    'â€¦': '…',
    'Ã—': '×',
    'âŒ˜': '⌘'
}

for root, _, files in os.walk(d):
    for f in files:
        if f.endswith('.tsx') or f.endswith('.ts'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            orig = content
            for k, v in reps.items():
                content = content.replace(k, v)
            if content != orig:
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(content)
                print(f'Updated {path}')
