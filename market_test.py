from SmartApi import SmartConnect
from dotenv import load_dotenv
import pyotp
import os

load_dotenv()

smart = SmartConnect(
    api_key=os.getenv("ANGEL_API_KEY")
)

session = smart.generateSession(
    os.getenv("ANGEL_CLIENT_CODE"),
    os.getenv("ANGEL_PIN"),
    pyotp.TOTP(
        os.getenv("ANGEL_TOTP_SECRET")
    ).now()
)

ltp = smart.ltpData(
    "NSE",
    "NIFTY",
    "99926000"
)

print("\n=== NIFTY LTP ===\n")
print(ltp)