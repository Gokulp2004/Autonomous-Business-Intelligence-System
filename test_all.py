import requests, json

# Dashboard Summary
r = requests.get('http://localhost:8000/api/dashboard/summary/94303ac1')
print('=== DASHBOARD SUMMARY ===')
print('Status:', r.status_code)
d = r.json()
for k, v in d.items():
    print(f'  {k}: {v}')

# Dashboard Charts
print('\n=== DASHBOARD CHARTS ===')
r2 = requests.get('http://localhost:8000/api/dashboard/charts/94303ac1')
print('Status:', r2.status_code)
d2 = r2.json()
charts = d2.get('charts', [])
print(f'Total charts: {len(charts)}')
for c in charts:
    print(f"  - {c.get('id','?')} | {c.get('chart_type','?')} | {c.get('title','?')[:50]}")

# Report Generation
print('\n=== PDF REPORT ===')
r3 = requests.post('http://localhost:8000/api/reports/generate/94303ac1?format=pdf')
print('Status:', r3.status_code)
print('Response:', r3.json())

print('\n=== PPT REPORT ===')
r4 = requests.post('http://localhost:8000/api/reports/generate/94303ac1?format=pptx')
print('Status:', r4.status_code)
print('Response:', r4.json())

# Download Reports
if r3.status_code == 200:
    url = r3.json()['download_url']
    r5 = requests.get(f'http://localhost:8000{url}')
    print(f'\nPDF Download: {r5.status_code} | {len(r5.content)} bytes')

if r4.status_code == 200:
    url = r4.json()['download_url']
    r6 = requests.get(f'http://localhost:8000{url}')
    print(f'PPT Download: {r6.status_code} | {len(r6.content)} bytes')

# Chat
print('\n=== CHAT ===')
r7 = requests.post('http://localhost:8000/api/chat/ask', json={
    'file_id': '94303ac1',
    'question': 'What are the top selling products?'
})
print('Status:', r7.status_code)
d7 = r7.json()
print('Error:', d7.get('error'))
print('Answer:', d7.get('answer', '')[:300])
print('Tools:', d7.get('tool_calls', []))
print('Suggestions:', d7.get('suggestions', []))

# Suggestions
print('\n=== SUGGESTIONS ===')
r8 = requests.get('http://localhost:8000/api/chat/suggestions/94303ac1')
print('Status:', r8.status_code)
print('Suggestions:', r8.json())
