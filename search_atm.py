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

for query in [
    "NIFTY",
    "NIFTY25",
    "NIFTY26",
    "NIFTYJUN",
    "NIFTY23200"
]:

    print("\n================")
    print("SEARCH:", query)
    print("================")

    try:
        result = smart.searchScrip(
            exchange="NFO",
            searchscrip=query
        )

        if result["data"]:
            print(result["data"][:10])

    except Exception as e:
        print(e)