import pandas as pd

df = pd.read_csv(
    "instruments.csv",
    low_memory=False
)

print(df.columns.tolist())