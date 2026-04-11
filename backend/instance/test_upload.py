import requests

url = "http://127.0.0.1:5000/upload"

files = {
    "image": open("test.jpg", "rb")   # 👈 image file name
}

data = {
    "caption": "My first post 🔥",
    "user_id": "1"
}

res = requests.post(url, files=files, data=data)

print(res.json())
