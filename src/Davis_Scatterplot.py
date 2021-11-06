import csv
import matplotlib.pyplot as plot
import numpy as numpy
from datetime import datetime
import random

authors = []
files = []
dates = []

with open("data/file_rootbeer.csv", mode='r') as file_rootbeer_csv:
    count = 1
    reader = csv.DictReader(file_rootbeer_csv)

    for rows in reader:
        if count == 1 or count % 2 == 1:
            count += 1
            continue

        if count > 100:
            break

        formatted_date = datetime.strptime((rows['Date'].replace('T', ' ')).replace('Z', ''), '%Y-%m-%d %H:%M:%S')

        authors.append(rows['Author'])
        files.append(rows['Filename'])
        dates.append(formatted_date)

        count += 1

file_names_dictionary = {}
named_files = []

counter = 1

for file in files:
    if file in file_names_dictionary:
        named_files.append(file_names_dictionary[file])
    else:
        file_names_dictionary[file] = 'F ' + str(counter)
        counter += 1
        named_files.append(file_names_dictionary[file])

colors_dictionary = {}
named_colors = []

for author in authors:
    if not author in colors_dictionary:
        colors_dictionary[author] = "%06x" % random.randint(0, 0xFFFFFF)
    named_colors.append('#' + colors_dictionary[author])

files_dates_dict = {}
files_with_dates = numpy.zeros(50)

for i in range(49, -1, -1):
    if not files[i] in files_dates_dict:
        files_dates_dict[files[i]] = dates[i]
    files_with_dates[i] = int((dates[i] - files_dates_dict[files[i]]).days / 7)

plot.scatter(named_files, files_with_dates, c=named_colors, s=50)
plot.xlabel("Files")
plot.ylabel("Time")
plot.show()
