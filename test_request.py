import requests
r = requests.post('http://localhost:8001/api/chat', json={
    'messages':[{'role':'user','content':'What is 2+2?'}],
    'active_specialists':['cmo']
})
print(r.status_code)
print(r.text)
