import csv
from datetime import datetime
from rtree import index
import sys
from vincenty import vincenty

class MatchWithOwiStep():
    max_distance_m = 200
    owis_per_day = {}
    tbnrs = {}
    i = 0

    def __init__(self, filename, tb_file):
        self.filename = filename
        self.tb_file = tb_file
    
    def set_up(self):
        with open(self.tb_file) as tbnr_file:
            tbnr_reader = csv.DictReader(tbnr_file, delimiter=',', quotechar='"')
            for row in tbnr_reader:
                self.tbnrs[row['TBNR']] = row['Tatbestandskategorie'] 

        # Import OWIs and index them
        with open(self.filename) as owi_file:
            owi_reader = csv.DictReader(owi_file, delimiter=',', quotechar='"')
            # iterate over every record and index it
            i = 0
            no_geocode = 0
            for row in owi_reader:
                date = row['tattag']
                idx = self.owis_per_day.get(date)
                if not idx:
                    idx = index.Index()
                    self.owis_per_day[date] = idx
                if not row['lat']:
                    #print("Ignoriere nicht geokodierte owi ", row)
                    no_geocode += 1
                    continue
                if row['tbnr1'].startswith('113'):
                    continue

                lat = float(row['lat'])
                lon = float(row['lon'])
                idx.insert(i, (lat, lon, lat, lon), obj = row)
                i += 1

            print("{} OWIs ohne Ortsangabe. Aussagen zur Match-Quote nur unter Vorbehalt möglich".format (no_geocode))

    def best_match(self, row, matches):
        rank = 0
        best_rank = 0
        best_match = None
        best_distance = None
        
        lat = float(row['latitude'])
        lon = float(row['longitude'])
            
        for match in matches:
            distance = vincenty((lat, lon), (float(match['lat']), float(match['lon']))) * 1000
            if (distance < self.max_distance_m):
                rank = 1 - distance / self.max_distance_m
                owi_time = datetime.strptime(match['tatzeit'], '%H:%M:%S')
                wegli_time = datetime.strptime(row['date'][11:19], '%H:%M:%S')

                # if timedelta is greater than an hour, we reduce rank value by 70%, 
                rank *= 0.3 + 0.7 * max(0, 1 - abs((owi_time - wegli_time).total_seconds())/3600)
                if rank > best_rank:
                    best_rank = rank
                    best_match = match
                    best_distance = distance

        return (best_match, best_distance, best_rank)

        
    def process(self, row):
        # filter record, if not in Stuttgart and not in 2020
        if row['city'] != 'Stuttgart' or row['date'][0:4] != '2020':
            return None
        # find index, depending on tree
        date = row['date'][0:10]
        print('Match ', row['city'], row['date'][0:10])
        idx = self.owis_per_day.get(date)
        if idx:
            lat = float(row['latitude'])
            lon = float(row['longitude'])
            
            matches = list(idx.nearest((lat, lon, lat, lon), 1, objects = 'raw'))
            (match, distance, rank) = self.best_match(row, matches)
            if match:
                row['owi_tatzeit'] = match['tatzeit']
                row['owi_tbnr'] = match['tbnr1']
                row['owi_tatort'] = match['tatort']
                row['owi_faz'] = match['faz']
                row['owi_distanz'] = distance
                row['owi_tbkat'] = self.tbnrs.get(match['tbnr1'])
                row['owi_match_guete'] = rank  
                
            print('Match ', distance, ' ', match)

            self.i += 1
            if self.i % 1000 == 0:
                print("{}: {} matched".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.i))
        return row

class WriteCsvStep():
    i = 0

    def __init__(self, filename, fieldnames):
        self.filename = filename
        self.fieldnames = fieldnames

    def set_up(self):
        self.outfile = open(self.filename, "w")
        self.writer = csv.DictWriter(self.outfile, self.fieldnames, restval='', delimiter=',', quotechar='"', extrasaction='ignore')
        self.writer.writeheader()

    def process(self, row):
        self.writer.writerow(row)
        self.i += 1
        if self.i % 1000 == 0:
            print("{}: {} written".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.i))
        return row


def process_rows(steps, rows):
    for step in steps:
        step.set_up()
    
    for row in rows:
        for step in steps:
            try:
                row = step.process(row)
                if not row:
                    break
            except Exception as e:
                row['error'] = sys.exc_info()[0]
                print("Unexpected error:", e, sys.exc_info()[0])


if __name__ == '__main__':
    print("{}: started".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    steps = [
        MatchWithOwiStep('../../verstoesse/out/parkverstoesse_2020_geocoded.csv',
            '../raw-data/tatbestaende_ruhender_verkehr.csv'),
        WriteCsvStep('out/matches.csv', ['date','owi_tatzeit', 'owi_match_guete',
            'charge', 'owi_tbnr','owi_tbkat','street', 'owi_tatort','owi_faz','owi_distanz',
            'city','zip','latitude','longitude'])
    ]

    with open("../../weg.li-republisher/out/notices-8.csv") as csvfile:
        wegli_reader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
        process_rows(steps, wegli_reader)