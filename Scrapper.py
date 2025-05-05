import requests
from bs4 import BeautifulSoup

def fetch_item_price(item_name):
    url = f"https://www.flipkart.com/search?q={item_name}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to load: {response.status_code}")
            return None
        soup = BeautifulSoup(response.content, "html.parser")
        price_tag = soup.find("div", class_="_30jeq3")
        if price_tag:
            price_text = price_tag.text.replace("₹", "").replace(",", "")
            return float(price_text)
        else:
            print("No price found")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# Simulate adding an item
item = input("Enter an item name (e.g., pencil): ")
price = fetch_item_price(item)
if price:
    print(f"Price of {item}: ₹{price:.2f}")
else:
    print(f"Couldn’t fetch price for {item}, defaulting to ₹50.00")