import pandas as pd

df = pd.read_csv("outputs/corner_delivery_features.csv")

print("=" * 60)
print("DELIVERY COMPLETION STATUS INSPECTION")
print("=" * 60)

print("\nDelivery completion status:")
print(df["delivery_completion_status"].value_counts(dropna=False))

print("\nCross-check against original pass outcome:")
print(
    pd.crosstab(
        df["pass_outcome"].fillna("[MISSING]"),
        df["delivery_completion_status"].fillna("[MISSING]"),
        margins=True
    )
)

print("\nMissing status and recipient:")
print(
    df[
        df["delivery_completion_status"].isna()
    ][["pass_outcome", "recipient"]].head(10)
)

print("\nFULL CROSS-TABULATION:")
print(
    pd.crosstab(
        df["pass_outcome"].fillna("[MISSING]").replace("", "[MISSING]"),
        df["delivery_completion_status"],
        margins=True
    )
)