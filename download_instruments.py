import requests
import pandas as pd

url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

print("Downloading instrument master...")

data = requests.get(url).json()

df = pd.DataFrame(data)

df.to_csv("instruments.csv", index=False)

print("Saved instruments.csv")
print("Rows:", len(df))