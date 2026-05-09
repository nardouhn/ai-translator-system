import requests
import time

def main():
    files = {'upload_file': ('test.txt', b'Hello world', 'text/plain')}
    data = {
        'source_lang': 'en',
        'target_lang': 'vi',
        'domain': 'general'
    }
    print("Sending request to /api/v1/file/translate...")
    try:
        response = requests.post('http://127.0.0.1:8000/api/v1/file/translate', files=files, data=data)
        print("Response:", response.status_code)
        print(response.text)
        
        if response.status_code == 200:
            file_id = response.json()['file_id']
            print(f"Checking status for {file_id}...")
            for i in range(10):
                time.sleep(2)
                res = requests.get(f'http://127.0.0.1:8000/api/v1/file/translate/{file_id}/status')
                print(res.text)
    except Exception as e:
        print("Error connecting:", e)

main()
