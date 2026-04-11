import requests

url = "http://127.0.0.1:5000/signup"

data = {
    "username": "thriveni01",
    "email": "ontipulithriveni@gmail.com",
    "password": "1234"
}

res = requests.post(url, json=data)

print(res.json())
