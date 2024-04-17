import os

from dotenv import load_dotenv
import json
import requests

from flask import Flask, request, jsonify, send_from_directory, Response


load_dotenv()
AUTH = os.environ.get("AUTH")
TOKEN = os.environ.get("TOKEN")

app = Flask(__name__)

headers = {
    "Authorization": f"Bot {TOKEN}",
    "Content-Type": "application/json"
}

@app.route("/upload", methods=["POST", "OPTIONS"])
def upload():
    if request.method == "OPTIONS":
        return enable_cors(Response()), 200
        
    elif request.method == "POST":
        print(request.headers.get("Authorization"))
        if request.headers.get("Authorization") != AUTH:
            response = jsonify({"Error": "Auth"})
            return enable_cors(response), 401
            
        data = json.loads(request.form.get("data"))
        config = json.loads(request.form.get("config"))
        
        for key in request.files:
            subject_name, subject_type = key.split(".")[1:]
            files = request.files.getlist(key)
            
            for subject in data:
                if subject["subject_name"] == subject_name and subject["subject_type"] == subject_type:
                    subject["files"] = files
                
        for subject in data:
            subject_name = subject["subject_name"]
            subject_type = subject["subject_type"]
            subject_date = subject["subject_date"]
            content_text = subject["content_text"] or "attachment"
            content_deadline = subject["content_deadline"]
            
            content = f"**[ {subject_date} ] {subject_type} **"
            
            if content_deadline:
                content = content + f"\nDEADLINE: {content_deadline}"
            
            content = content + f"\n>>> {content_text}"
            
            subject_channel = config[subject_name]["discord_channel"]
            message = send_message(subject_channel, content)
            
            if "files" in subject:
                thread = create_thread(subject_channel, message["id"])
                for file in subject["files"]:
                    print(file)
                    file.name = file.filename
                    send_attachment(thread["id"], file)
                close_thread(subject_channel, thread["id"])
                
        
        response = jsonify({"data": request.form.get("text")})
        return enable_cors(response), 200
        
@app.route("/fetch", methods=["POST", "OPTIONS"])
def fetch():
    if request.method == "OPTIONS":
        return enable_cors(Response()), 200
        
    elif request.method == "POST":
        print(request.headers.get("Authorization"), AUTH)
        if request.headers.get("Authorization") != AUTH:
            response = jsonify({"Error": "Auth"})
            return enable_cors(response), 401
            
        config = json.loads(request.form.get("config"))
        data = []
        
        for subject in config:
            discord_channel_id = config[subject]["discord_channel"]
            messages_list = get_all_messages(discord_channel_id)
            
            for message in messages_list:
                entry_parts = message["content"].split("\n")
                
                entry_head = entry_parts[0]
                entry_deadline = None
                entry_body = []
                
                if "DEADLINE:" in entry_parts[1]:
                    entry_deadline = entry_parts[1].split(" ")[1]
                    entry_body = "\n".join(entry_parts[2:])
                else:
                    entry_deadline = None
                    entry_body = "\n".join(entry_parts[1:])
                    
                entry_body = entry_body.replace(">>> ", "")
                
                entry_head_parts = entry_head.split(" ")
                entry_date = entry_head_parts[1]
                entry_type = entry_head_parts[3]
        
                entry_data = {
                    "subject_name": subject,
                    "subject_date": entry_date,
                    "subject_type": entry_type,
                    "subject_deadline": entry_deadline,
                    "subject_body": entry_body,
                    "subject_files": []
                    }
                    
                data.append(entry_data)
                
        data = jsonify(data)
        return enable_cors(data)
        
def enable_cors(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    return response

def send_message(channel_id, message_content):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    
    payload = {
        "content": message_content
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response.json()

def send_attachment(channel_id, file):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    
    headers_copy = headers.copy()
    headers_copy.pop("Content-Type", None)
    
    files = {
        "file": file
    }
    
    response = requests.post(url, headers=headers_copy, files=files)
    return response.json()

def create_thread(channel_id, message_id):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}/threads"

    payload = {
        "name": "Attachments",
        "auto_archive_duration": 60
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response.json()

def close_thread(channel_id, thread_id):
    url = f"https://discord.com/api/v9/channels/{thread_id}"
    payload = {
        "archived": True
    }
    response = requests.patch(url, headers=headers, data=json.dumps(payload))
    print(response.text)
    return response.json()
    
def get_all_messages(channel_id):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    params = {"limit": 100}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

if __name__ == "__main__":
    app.run(debug=True)