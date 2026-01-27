import json
from datetime import datetime
import matplotlib.pyplot as plt

def parse_date(s: str)-> datetime:
    return datetime.fromisoformat(s.replace('Z', '+00:00'))

def main():
    # load the touch records 
    with open("data/file_touches.json", "r", encoding="utf-8") as f:
        touches = json.load(f)

    if not touches:
        print('No touch data found')
        return 
    
    files = sorted({t["file"] for t in touches})
    file_to_y = {fname: i for i, fname in enumerate(files)}

    # compute earliest touch date
    all_dates = [parse_date(t["date"]) for t in touches]
    start_date = min(all_dates)

    # grouping points by author and everyone gets their own color
    by_author = {}
    for t in touches:
        dt = parse_date(t["date"])
        week = (dt - start_date).days // 7
        y = file_to_y[t["file"]]
        author = t.get("author", "unknown")

        by_author.setdefault(author, {"x": [], "y": []})
        by_author[author]["x"].append(week)
        by_author[author]["y"].append(y)

    # plotting
    for author, pts in by_author.items():
        plt.scatter(pts["x"], pts["y"], label=author, alpha=0.7, s=18)

    plt.xlabel("Weeks since project start (week 0 = earliest commit)")
    plt.ylabel("File")
    plt.title("Rootbeer source-file touches over time (colored by author)")

    # If there are lots of authors, legend can get huge — still required, but smaller.
    plt.legend(loc="best", fontsize="small")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()