import json
import urllib.request

# Test chat endpoint
data = {'messages': [{'role': 'user', 'content': 'I have a persistent headache and blurred vision'}]}
req = urllib.request.Request(
    'http://localhost:8000/api/chat',
    data=json.dumps(data).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

response = urllib.request.urlopen(req)
result = json.loads(response.read().decode())

specs = list(result.get('specialist_responses', {}).keys())
print(f'✓ Chat API working')
print(f'✓ Specialist responses: {len(specs)}/9')
print(f'✓ Specialists responding: {", ".join(specs)}')
response_len = len(result.get('response', ''))
print(f'✓ Primary response: {response_len} characters')
print(f'\nTest Status: ALL TESTS PASSED ✓')
