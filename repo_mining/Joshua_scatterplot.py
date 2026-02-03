import csv
import matplotlib.pyplot as plt
from datetime import datetime

from datetime import datetime

def date_to_week(date_str):
    dt = datetime.strptime(date_str[:-6], "%a %b %d %H:%M:%S %Y")
    return dt.isocalendar()[1]  # week number

files = set()
rows = []

with open("file_touches.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        files.add(row["file"])
        rows.append(row)

file_ids = {f: i for i, f in enumerate(sorted(files))}

data = {}
for row in rows:
    author = row["author"]
    week = date_to_week(row["date"])
    file_id = file_ids[row["file"]]

    if author not in data:
        data[author] = ([], [])

    data[author][0].append(week)      # X values
    data[author][1].append(file_id)   # Y values

plt.figure(figsize=(10, 6))

for author in data:
    plt.scatter(
        data[author][1],
        data[author][0],
        label=author,
        alpha=0.7
    )

plt.ylabel("Week of Year")
plt.xlabel("File ID")
plt.title("File Touches Over Time (Colored by Author)")
plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
plt.tight_layout()
plt.show()
