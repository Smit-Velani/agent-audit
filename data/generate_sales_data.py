import pandas as pd
import numpy as np

rng = np.random.default_rng(7)
n = 120
regions = rng.choice(["North", "South", "East", "West"], n)
products = rng.choice(["Widget A", "Widget B", "Widget C"], n)
segments = rng.choice(["Enterprise", "SMB", "Consumer"], n, p=[0.2, 0.3, 0.5])
units_sold = rng.integers(1, 50, n)
unit_price = rng.choice([19.99, 29.99, 49.99], n)
revenue = (units_sold * unit_price).round(2)
dates = pd.date_range("2026-01-01", periods=n, freq="D")

df = pd.DataFrame({
    "order_id": range(1001, 1001 + n),
    "order_date": dates.strftime("%Y-%m-%d"),
    "region": regions,
    "product": products,
    "customer_segment": segments,
    "units_sold": units_sold,
    "revenue": revenue,
})
df.to_csv("data/sales_data.csv", index=False)
print(df.head())
print(df.shape)