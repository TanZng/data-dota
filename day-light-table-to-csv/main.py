import csv

fcsv = open('table.csv', 'w')
writer = csv.writer(fcsv)
with open('table.txt') as f:
    for line in f:
        x = line.split("\t")
        x.pop()
        x[-1] = float(x[-1].replace(",", ""))
        print(x)
        writer.writerow(x)

fcsv.close()