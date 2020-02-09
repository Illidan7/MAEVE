import requests

url = "https://api.telegram.org/*****"

def sendMessage(chat, text):
    params = {'chat_id': chat, 'text': text}
    response = requests.post(url + 'sendMessage', data=params)
    return response
