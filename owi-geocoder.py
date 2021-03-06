# coding=utf-8
import osmnx as ox
import argparse
import os, re, csv
import pandas as pd 
from functools import lru_cache
from photon import Photon
from datetime import datetime
import sys
import h3
import holidays

HNR_REGEX = re.compile("([- \.A-Za-zäÄüÜöÖß]+) hnr (\d+[A-Za-z-]*\d*)", re.UNICODE)
HNR_WITHOUT_HNR_REGEX = re.compile("([- \.A-Za-zäÄüÜöÖß]+)(\d+[A-Za-z-]*\d*)", re.UNICODE)
INTERSECTION_REGEX = re.compile("([- \.A-Za-z0-9äÄüÜöÖß]+)(ecke | ?/ ?| einmündung )([- \.A-Za-z0-9äÄüÜöÖß]+)", re.UNICODE)
STREET_ONLY = re.compile("([-\.A-Za-zäÄüÜöÖß]+$)|([-\.A-Za-zäÄüÜöÖß]+er straße$)")
OPPOSITE_REGEX = re.compile(" gegenüber | gg |geg.|ggü.")

class Step():
    def set_up(self):
        None

class SimpleParseStep(Step):

    def __init__(self, street_column, housenumber_column):
        self.street_column = street_column
        self.housenumber_column = housenumber_column

    def normalize(self, input):
        input = input.lower()
        input = input.replace(',', ' ')
        input = input.replace(' neben ', ' ')
        input = input.replace(' höhe ', ' ')
        input = input.replace(' flur: ', ' ')
        input = input.replace(' flurstücksnummer: ', ' ')
        input = input.replace(' gemarkung ', ' ')
        input = input.replace(' bereich vz 283', ' ')
        input = input.replace('hausnummer', 'hnr')
        input = input.replace('str.', 'straße ')
        input = input.replace(' gegenüber ', ' ') # information is already extracted
        input = input.replace(' gg ', ' ') # information is already extracted
        input = input.replace('geg.', ' ') # information is already extracted
        input = input.replace('ggü.', ' ') # information is already extracted
        input = input.replace(' auf dem parkplatz', ' ') # information is already extracted
        input = input.replace(' parkplatz', ' ') # information is already extracted
        input = input.replace(' parkhaus', ' ') # information is already extracted
        input = input.replace(' (ca) ', ' ')
        input = input.replace(' hnr ', ' ')
        input = input.replace(' psa ', ' ')
        input = input.replace(' parkscheinautomat ', ' ')

        return input

    def process(self, row):
        row['type'] = 'hnr'
        row['street'] = row[self.street_column]
        row['hnr'] = row[self.housenumber_column]

        return row

class ParseStep(SimpleParseStep):

    def __init__(self, place_column_name):
        self.place_col = place_column_name
    
    def figure_out_type(self, input, input_normalized):
        if " psa " in input or " parkscheinautomat " in input:
            return "psa"
        elif " ecke " in input or "/" in input or " einmündung " in input:
            return "intersection"
        elif "parkplatz" in input or "parkhaus" in input:
            return "parking"
        elif (HNR_REGEX.search(input) or HNR_WITHOUT_HNR_REGEX.search(input)) and HNR_WITHOUT_HNR_REGEX.search(input_normalized):
            return "hnr"
        elif STREET_ONLY.match(input):
            return "street"
        else:
            return "?" 

    def first_street(self, result):
        input = result['input_normalized']
        if result['type'] in ['hnr', 'psa']:
            street = HNR_WITHOUT_HNR_REGEX.search(input).group(1)
        elif result['type'] == 'intersection':
            street = INTERSECTION_REGEX.search(input).group(1)
        else:
            street = input

        return street.strip()

    def process(self, row):
        input = row[self.place_col].lower()
        intersection_match = INTERSECTION_REGEX.search(input)
        row['is_opposite'] = OPPOSITE_REGEX.search(input) != None
        row['input_normalized'] = self.normalize(input)
        row['type'] = self.figure_out_type(input, row['input_normalized'])
        row['street'] = self.first_street(row)
        row['street2'] = intersection_match.group(3) if intersection_match else None
        hnr_search = (HNR_REGEX.search(input) or HNR_WITHOUT_HNR_REGEX.search(input))
        row['hnr'] = hnr_search.group(2) if hnr_search else None

        return row

class GeocodePsaStep(Step):
   
    # GeoPandasDataFrame containing all parking tickets machines
    vending_machines_gdf = None
    
    def __init__(self, place):
        self.place = place

    def set_up(self):
        def name(names):
            if not names:
                return ''
            elif isinstance(names, str):
                return names
            else:
                return ' '.join(names)

        tags = {'amenity': "vending_maching", "vending": "parking_tickets"}
        self.vending_machines_gdf = ox.geometries_from_place(self.place, tags)
        G = ox.graph_from_place(self.place, network_type='drive', retain_all = True, simplify=True)
        nearest_edges = ox.get_nearest_edges(G, self.vending_machines_gdf['geometry'].x, self.vending_machines_gdf['geometry'].y , method='balltree')
        self.vending_machines_gdf['street'] = [*map(lambda x: name(G.edges[(x[0], x[1], x[2])].get("name")).lower(), nearest_edges)]

    def geocode(self, street, psa_nr):
        matching_psas = self.vending_machines_gdf[self.vending_machines_gdf.ref == psa_nr]
        if len(matching_psas) > 0:    
            return matching_psas.iloc[0]
        else:
            psas_in_street = self.vending_machines_gdf[self.vending_machines_gdf.street.str.contains(street)]
            if len(psas_in_street) > 0:  
                return psas_in_street.iloc[0]
        return None

    def process(self, row):
        if row.get('type') != 'psa':
            return row

        psa = self.geocode(row['street'], row['hnr'])
        if isinstance(psa, pd.Series):
            row['lat'] = psa.geometry.y
            row['lon'] = psa.geometry.x
            row['geocoded_street'] = psa["street"]
    
        return row


class GeocodeAddressStep(Step):
    force = False
    geolocator = None

    def __init__(self, geolocator, bbox = None, force=False, address_append=''):
        self.geolocator = geolocator
        self.force = force
        self.bbox = bbox
        self.address_append = address_append

    @lru_cache(maxsize=2048)
    def geocode_address(self, address):
        return self.geolocator.geocode(address, exactly_one=True, bbox=self.bbox)

    def call_geocoder(self, address, fallback_address = None):
        print(address+ ' '+self.address_append)
        loc = self.geocode_address(address+ ' '+ self.address_append)
        return loc if loc or not fallback_address else self.geocode_address(fallback_address + self.address_append)

    def geocode(self, result):
        if result['type'] == 'hnr':
            # geocode street+hnr, fallback street only
            return self.call_geocoder(result['street']+ " "+result['hnr'])
        elif result['type'] in ['street', '?']:
            # TODO geocode street+poi, fallback street only
            return self.call_geocoder(result['street'])
        elif result['type'] == 'psa' and not result.get('lat'):
            # fallback street only
            return self.call_geocoder(result['street'])
        elif result['type'] == 'parking':
            # overpass-query, fallback street only
            return self.call_geocoder(result['street'])
        elif result['type'] == 'intersection':
            # TODO
            # fallback street only
            return self.call_geocoder(result['street'])
        else:
            return None
        
    def process(self, row):
        if not self.force and row.get('lat'):
            return row

        geocoded_row = self.geocode(row)

        row['lat'] = geocoded_row.latitude if geocoded_row else None
        row['lon'] = geocoded_row.longitude if geocoded_row else None
        row['geocoded_postcode'] = geocoded_row.raw["properties"].get("postcode") if geocoded_row else None
        row['geocoded_city'] = geocoded_row.raw["properties"].get("city") if geocoded_row else None
        row['geocoded_name'] = geocoded_row.raw["properties"].get("name") if geocoded_row else None
        row['geocoded_hnr'] = geocoded_row.raw["properties"].get("housenumber") if geocoded_row else None
        row['geocoded_street'] = geocoded_row.raw["properties"].get("street") if geocoded_row else None
        row['geocoded_district'] = geocoded_row.raw["properties"].get("district") if geocoded_row else None
        
        return row

class AddH3CodeStep(Step):
    def __init__(self, resolution : int = 8):
        self.resolution = resolution
        self.column_name = 'h3_{}'.format(resolution)

    def process(self, row):
        if row and row['lat'] and row['lon']:
            row[self.column_name] = h3.geo_to_h3(float(row['lat']), float(row['lon']), self.resolution)
        return row

class TimeSlotStep(Step):
    """
        Adds the following columns:
        - weekday
        - weekday_cat: 
        - hour:
        - day_of_year:
    """
    def __init__(self, date_column: str, hour_column: str, country: str, subdiv: str = None):
        self.holidays = holidays.country_holidays(country, subdiv=subdiv)
        self.date_column = date_column
        self.hour_column = hour_column
        
    def process(self, row):
        timetuple = datetime.strptime(row[self.date_column], '%Y-%m-%d').timetuple()
        row['weekday'] = timetuple.tm_wday
        if timetuple.tm_wday == 6 or row[self.date_column] in self.holidays:
            row['weekday_cat'] = 6
        elif timetuple.tm_wday == 5:
            row['weekday_cat'] = 5
        else:
            row['weekday_cat'] = 0
        row['day_of_year'] = timetuple.tm_yday
        row['hour'] = row[self.hour_column].split(':')[0]
        
        return row
    
class PrintStep(Step):
   
    def process(self, row):
        print(row)
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
            print("{}: {} geocoded".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.i))
        return row

def process_rows(steps, rows):
    for step in steps:
        step.set_up()
    
    for row in rows:
        for step in steps:
            try:
                row = step.process(row)
            except Exception as e:
                row['error'] = sys.exc_info()[0]
                print("Unexpected error:", e)
                import traceback
                print(traceback.format_exc())
                raise e

def main(address_column, osm_region_name, out_filename, input_filename, geocoder_url):
    print("{}: started".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    steps = [
        ParseStep(address_column),
        GeocodePsaStep(osm_region_name),
        GeocodeAddressStep(
            Photon(user_agent="owi-geocoder", domain=geocoder_url),
            ["48.68,8.96","48.87,9.4"],
            force = False,
            address_append = osm_region_name
            ),
        TimeSlotStep('Tattag','Tatzeit', 'DE', 'BW'),
        AddH3CodeStep(8),
        AddH3CodeStep(9),
        WriteCsvStep(out_filename, ['FAZ','Tattag','Tatzeit','Tatort','TBNR1','SummeSoll','SummeIst','Status','Rechtsgebiet','type', 'street', 'hnr', 'street2', 'is_opposite', 'input_normalized', 'lat', 'lon', 'geocoded_postcode','geocoded_city','geocoded_street','geocoded_hnr','geocoded_name','geocoded_district','error',
            'h3_8', 'h3_9', 'weekday', 'weekday_cat', 'hour', 'day_of_year'])
    ]        

    # Köln
    # steps= [
    #    SimpleParseStep(),
    #    GeocodeAddressStep(
    #        Photon(user_agent="owi-geocoder", domain=geocoder_url),
    #        ["50.8079,6.7865","51.0873,7.2245"],
    #        force = False,
    #        address_append = osm_region_name
    #        ),
    #    WriteCsvStep(out_filename, ['datum_von','Kennzeichen1','fahrzeugart','fabrikat','strasse','hausnummer','tatbestand1','tatbestand2','tatbestand3', 'lat', 'lon', 'geocoded_postcode','geocoded_city','geocoded_street','geocoded_hnr','geocoded_name','geocoded_district','error'])
    #]

    with open(input_filename) as csvfile:
        locations_reader = csv.DictReader(csvfile, delimiter=',', quotechar='"')
        process_rows(steps, locations_reader)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', dest='address_column', default='Tatort')
    parser.add_argument('-r', dest='osm_region_name', default='Stuttgart, Deutschland')
    parser.add_argument('-o', dest='out_filename', default='out/parkverstoesse_2020_geocoded.csv')
    parser.add_argument('-i', dest='input_filename', default='data/parkverstoesse_2020_sorted.csv')
    parser.add_argument('-g', dest='geocoder_url', default='photon.stadtnavi.eu')
    
    args = parser.parse_args()
    main(args.address_column, args.osm_region_name, args.out_filename, args.input_filename, args.geocoder_url)


