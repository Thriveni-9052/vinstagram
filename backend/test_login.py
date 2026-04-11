import requests

url = "http://127.0.0.1:5000/login"

data = {
    "username": "venka",
    "password": "1234"
}

res = requests.post(url, json=data)

print(res.json())
