from SmartApi import SmartConnect
from dotenv import load_dotenv
import pyotp
import os

load_dotenv()

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE")
PIN = os.getenv("ANGEL_PIN")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

print("Generating TOTP...")

totp = pyotp.TOTP(TOTP_SECRET).now()

print("Connecting to Angel One...")

smart = SmartConnect(api_key=API_KEY)

session = smart.generateSession(
    CLIENT_CODE,
    PIN,
    totp
)

print("\nLOGIN SUCCESSFUL\n")

print("Login successful")
print("Client:", session["data"]["clientcode"])