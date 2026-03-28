import os
import json
import urllib.request
import urllib.error

def main():
    url = os.environ.get('BASE_URL', 'http://127.0.0.1:8000/api/base')
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            raw = resp.read()
    except urllib.error.URLError as e:
        print('Error:', getattr(e, 'reason', str(e)))
        return 1
    try:
        data = json.loads(raw.decode('utf-8'))
    except Exception as e:
        print('DecodeError:', str(e))
        return 2
    os.makedirs('tests', exist_ok=True)
    out_path = os.path.join('tests', 'base_dump.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('Saved:', out_path)
    print('Categories:', len(data))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
