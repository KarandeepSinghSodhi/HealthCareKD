import urllib.request
import json
import time

# Wait for backend to fully start
time.sleep(2)

# Test streaming endpoint
try:
    data = {'messages': [{'role': 'user', 'content': 'I have chest pain and dizziness'}]}
    req = urllib.request.Request(
        'http://localhost:8000/api/chat-stream',
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    response = urllib.request.urlopen(req)
    
    print('✓ Streaming endpoint responding')
    print('Reading events...\n')
    
    event_count = 0
    specialists_responded = []
    error_msg = None
    
    for line in response:
        line = line.decode('utf-8').strip()
        if line.startswith('data: '):
            event_count += 1
            try:
                event_data = json.loads(line[6:])
                event_type = event_data.get('event', 'unknown')
                print(f'Event {event_count}: {event_type}')
                
                if event_type == 'error':
                    error_msg = event_data.get('message', 'Unknown error')
                    print(f'  ✗ Error: {error_msg}')
                    break
                
                elif event_type == 'specialist_response':
                    specialist_id = event_data.get('specialist_id')
                    specialists_responded.append(specialist_id)
                    response_text = event_data.get('response', '')
                    preview = response_text[:40] + '...' if len(response_text) > 40 else response_text
                    print(f'  → {specialist_id}: {preview}')
                
                elif event_type == 'triage_complete':
                    selected = event_data.get('specialists', [])
                    print(f'  → Selected {len(selected)} specialists: {selected}')
                
                elif event_type == 'complete':
                    total_calls = event_data.get('total_calls', '?')
                    print(f'  → Complete! Total API calls: {total_calls}')
                    print(f'  → Specialists responded: {specialists_responded}')
                    break
            except json.JSONDecodeError as e:
                print(f'  Error parsing JSON: {e}')
    
    print(f'\n✓ Test Complete: {event_count} events received')
    if error_msg:
        print(f'✗ Stream error: {error_msg}')
    else:
        print(f'✓ Specialists responded: {len(specialists_responded)}/9')
    
except Exception as e:
    import traceback
    print(f'✗ Error: {e}')
    traceback.print_exc()
