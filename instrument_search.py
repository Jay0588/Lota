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

print("Searching instruments...")

try:
    result = smart.searchScrip(
        exchange="NFO",
        searchscrip="NIFTY"
    )

    print(result)

except Exception as e:
    print("ERROR:")
    print(e)