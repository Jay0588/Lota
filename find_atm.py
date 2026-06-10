from SmartApi import SmartConnect
from dotenv import load_dotenv
import pyotp
import os

load_dotenv()

smart = SmartConnect(
    api_key=os.getenv("ANGEL_API_KEY")
)

smart.generateSession(
    os.getenv("ANGEL_CLIENT_CODE"),
    os.getenv("ANGEL_PIN"),
    pyotp.TOTP(
        os.getenv("ANGEL_TOTP_SECRET")
    ).now()
)

# Live NIFTY
ltp = smart.ltpData(
    "NSE",
    "NIFTY",
    "99926000"
)

price = ltp["data"]["ltp"]

atm = round(price / 50) * 50

print("\nNIFTY:", price)
print("ATM STRIKE:", atm)