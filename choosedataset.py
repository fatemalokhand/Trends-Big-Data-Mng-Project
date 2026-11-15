
import requests
import pandas as pd

# StatsBomb Open Data
URL = (
    "https://raw.githubusercontent.com/"
    "hudl/open-data/master/data/competitions.json"
)

# Download competition information
response = requests.get(URL)
response.raise_for_status()

competitions = pd.DataFrame(response.json())

# Display useful columns
columns = [
    "competition_id",
    "competition_name",
    "season_id",
    "season_name",
    "country_name",
    "match_available_360"
]

# Keep only columns that exist
columns = [c for c in columns if c in competitions.columns]

print("\nAVAILABLE COMPETITIONS AND SEASONS\n")

print(
    competitions[columns]
    .sort_values(["competition_name", "season_name"])
    .to_string(index=False)
)

# Save the list
competitions[columns].to_csv(
    "available_competitions.csv",
    index=False
)

print("\nSaved to available_competitions.csv")
