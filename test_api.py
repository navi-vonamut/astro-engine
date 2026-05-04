import requests

def test_connection():
    try:
        response = requests.get("https://google.com", timeout=10)
        print(f"Status Code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_connection()
