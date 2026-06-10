import pandas as pd

df = pd.read_csv("instruments.csv")

# Only NIFTY options
nifty = df[
    df["symbol"].astype(str).str.contains("NIFTY", na=False)
]

# Only options
nifty = nifty[
    nifty["instrumenttype"].astype(str).str.contains("OPT", na=False)
]

print("\nTOTAL NIFTY OPTIONS:")
print(len(nifty))

print("\nFIRST 20:")
print(
    nifty[
        ["symbol", "token"]
    ].head(20)
)