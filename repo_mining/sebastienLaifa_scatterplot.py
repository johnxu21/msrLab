import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm

# Load the authors_file_touches CSV
csv_file = "data/authors_file_touches.csv"
df = pd.read_csv(csv_file)

# Convert Date column to datetime
df['Date'] = pd.to_datetime(df['Date'])

# Compute week number since the start of the project
start_date = df['Date'].min()
df['Week'] = ((df['Date'] - start_date).dt.days // 7) + 1

# Count how many times each file was touched per week
df['Touches'] = df.groupby(['Filename', 'Week', 'Author'])['Author'].transform('count')

# Assign each file a unique x-axis index (1 to 26)
file_to_x = {file: idx+1 for idx, file in enumerate(df['Filename'].unique())}
df['FileIndex'] = df['Filename'].map(file_to_x)

# Assign each author a distinct color
authors = df['Author'].unique()
colors = plt.get_cmap('tab20', len(authors))
author_color_map = {author: colors(i) for i, author in enumerate(authors)}
df['Color'] = df['Author'].map(author_color_map)

# Create scatter plot
plt.figure(figsize=(15, 8))
for author in authors:
    author_data = df[df['Author'] == author]
    plt.scatter(
        author_data['FileIndex'],
        author_data['Week'],
        s=50 * author_data['Touches'],  # size the dot by number of touches
        color=author_color_map[author],
        label=author
    )

# Set x-axis ticks to numbers 1 to 26
plt.xticks(ticks=list(range(1, len(file_to_x)+1)))

# Add labels and title
plt.xlabel('File')
plt.ylabel('Weeks')
plt.title('File Touches by Week and Author')

# Add legend
plt.legend(title='Author', bbox_to_anchor=(1.05, 1), loc='upper left')

# Adjust layout and save figure
plt.tight_layout()
plt.savefig("data/scatterplot_file_touches.png")
plt.show()
