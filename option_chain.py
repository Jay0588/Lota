import pandas as pd
import pyotp
import os

from dotenv import load_dotenv
from SmartApi import SmartConnect

# =========================
# LOAD ENV
# =========================

load_dotenv()

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE")
PIN = os.getenv("ANGEL_PIN")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

# =========================
# LOGIN
# =========================

print("Connecting to Angel One...")

smart = SmartConnect(
    api_key=API_KEY
)

smart.generateSession(
    CLIENT_CODE,
    PIN,
    pyotp.TOTP(
        TOTP_SECRET
    ).now()
)

print("Login Successful")

# =========================
# GET LIVE NIFTY
# =========================

nifty_data = smart.ltpData(
    "NSE",
    "NIFTY",
    "99926000"
)

nifty_price = nifty_data["data"]["ltp"]

atm = round(nifty_price / 50) * 50

print("\n==========================")
print("NIFTY")
print("==========================")

print(f"NIFTY LTP : {nifty_price}")
print(f"ATM STRIKE: {atm}")

# =========================
# LOAD INSTRUMENT MASTER
# =========================

print("\nLoading instruments...")

df = pd.read_csv(
    "instruments.csv",
    low_memory=False
)

# =========================
# FILTER NIFTY OPTIONS
# =========================

options = df[
    (df["name"] == "NIFTY")
    &
    (df["instrumenttype"].astype(str).str.contains("OPT"))
].copy()

# strike is stored x100

options["strike"] = (
    pd.to_numeric(
        options["strike"],
        errors="coerce"
    ) / 100
)

# =========================
# FIND ATM CONTRACTS
# =========================

atm_options = options[
    options["strike"] == atm
].copy()

if len(atm_options) == 0:

    print("\nNo ATM contracts found.")
    quit()

atm_options["expiry"] = pd.to_datetime(
    atm_options["expiry"],
    errors="coerce"
)

atm_options = atm_options.sort_values(
    "expiry"
)

nearest_expiry = atm_options.iloc[0]["expiry"]

atm_options = atm_options[
    atm_options["expiry"] == nearest_expiry
]

# =========================
# FIND CE AND PE
# =========================

ce = atm_options[
    atm_options["symbol"].str.endswith("CE")
].iloc[0]

pe = atm_options[
    atm_options["symbol"].str.endswith("PE")
].iloc[0]

# =========================
# FETCH LIVE OPTION PRICES
# =========================

ce_ltp = smart.ltpData(
    "NFO",
    ce["symbol"],
    str(ce["token"])
)

pe_ltp = smart.ltpData(
    "NFO",
    pe["symbol"],
    str(pe["token"])
)

ce_price = ce_ltp["data"]["ltp"]
pe_price = pe_ltp["data"]["ltp"]

# =========================
# OUTPUT
# =========================

print("\n==========================")
print("OPTION CHAIN")
print("==========================")

print(f"Expiry : {nearest_expiry.date()}")

print("\nCALL OPTION")
print(f"Symbol : {ce['symbol']}")
print(f"Token  : {ce['token']}")
print(f"LTP    : {ce_price}")

print("\nPUT OPTION")
print(f"Symbol : {pe['symbol']}")
print(f"Token  : {pe['token']}")
print(f"LTP    : {pe_price}")

print("\n==========================")
print("SUMMARY")
print("==========================")

print(f"NIFTY     : {nifty_price}")
print(f"ATM       : {atm}")
print(f"CE PRICE  : {ce_price}")
print(f"PE PRICE  : {pe_price}")

if ce_price > pe_price:

    print("\nBias: BULLISH")

elif pe_price > ce_price:

    print("\nBias: BEARISH")

else:

    print("\nBias: NEUTRAL")