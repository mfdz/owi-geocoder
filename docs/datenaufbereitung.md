## Datenaufbereitung

Städte stellen die Daten in sehr unterschiedlicher Form und mitunter mit Formatierungsfehlern bereit.

Der owi-geocoder erwartet die Daten eines Jahres in einer zusammengeführten CSV-Datei mit entweder einer Ortsspalte oder zwei Spalten für Straße und Hausnummer. Zur schnelleren Verortung sollten die Datensätze alphabetisch nach der Address-Spalte sortiert sein. Dies ermöglicht ein effizientes Caching bereits geokodierter Adressen, die damit nicht meehrfach angefragt werden müssen.


### Datenaufbereitung Köln
Die Kölner Daten sind als monatsweise CSV-Dateien über das Download-Portal https://www.offenedaten-koeln.de herunterladbar.
Mit nachfolgenden Schritten (erfordern den Kommandozeilen-Client curl zum Download) laden wir sie herunter und hängen für die Monate Februar-Dezember die Daten ohne die Kopfzeile in einer Datei an. Abschließend sortieren wir die Datensätze mittels `csvsort` nach den Spalten `strasse` und `hausnummer`.

```
curl https://www.offenedaten-koeln.de/sites/default/files/RV_Januar_Koeln_2019.csv > Koeln_2019.csv
curl https://www.offenedaten-koeln.de/sites/default/files/RV_Februar_Koeln_2019.csv | tail -n+2 >> Koeln_2019.csv
curl https://www.offenedaten-koeln.de/sites/default/files/RV_Maerz_Koeln_2019.csv | tail -n+2 >> Koeln_2019.csv
curl https://www.offenedaten-koeln.de/sites/default/files/RV_April_Koeln_2019.csv | tail -n+2 >> Koeln_2019.csv
curl https://www.offenedaten-koeln.de/sites/default/files/RV_Mai_Koeln_2019.csv | tail -n+2 >> Koeln_2019.csv
curl https://www.offenedaten-koeln.de/sites/default/files/RV_Juni_Koeln_2019.csv | tail -n+2 >> Koeln_2019.csv
curl https://www.offenedaten-koeln.de/sites/default/files/RV_Juli_Koeln_2019.csv | tail -n+2 >> Koeln_2019.csv
curl https://www.offenedaten-koeln.de/sites/default/files/RV_August_Koeln_2019.csv | tail -n+2 >> Koeln_2019.csv
curl https://www.offenedaten-koeln.de/sites/default/files/RV_Oktober_Koeln_2019.csv | tail -n+2 >> Koeln_2019.csv
curl https://www.offenedaten-koeln.de/sites/default/files/RV_November_Koeln_2019.csv | tail -n+2 >> Koeln_2019.csv
curl https://www.offenedaten-koeln.de/sites/default/files/RV_Dezember_Koeln_2019.csv | tail -n+2 >> Koeln_2019.csv

csvsort -c strasse,hausnummer Koeln_2019.csv > Koeln_2019_sorted.csv
```


### Datenaufbereitung Stuttgart
Die Stadt Stuttgart stellt die Daten im für die automatisierte Verarbeitung etwas mühsamer zu handhabenden Excel-Format bereit, das zudem noch einige Datenfehler enthält, die wir mit folgenden Schritten bereinigen:

1. Aus Datei "Halt und Parkverstöße Stuttgart.xlsx" Tabellenblatt 2020 als parkverstoesse_2020.csv exportieren
2. Mittels `tail -n+5 parkverstoesse_2020.csv > parkverstoesse_2020_.csv` Kopfzeilen entfernen
3. Datums-/Zeitfelder bereinigen (erfordert installiertes [cvskit](https://csvkit.readthedocs.io/en/latest/))

```sh
paste -d, \
    <( csvcut -c 1 -d ';' parkverstoesse_2020_.csv ) \
    <( csvcut -c 2 -d ';' parkverstoesse_2020_.csv | cut -c1-10 ) \
    <( csvcut -c 3 -d ';' parkverstoesse_2020_.csv | cut -c12-19 | tail -n+2 | sed '1 s/^/Tatzeit\n/') \
    <( csvcut -c 4- -d ';' parkverstoesse_2020_.csv ) | csvformat -D ',' > parkverstoesse_2020_cleaned.csv

sed -i '' 's/\. Okt/.10/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/\. Jan,/.01,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/\. Feb,/.02,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/\. Mär,/.03,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/\. Apr,/.04,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/\. Mai,/.05,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/\. Jun,/.06,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/\. Jul,/.07,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/\. Aug,/.08,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/\. Sep,/.09,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/\. Nov,/.11,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/\. Dez,/.12,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/Nov 30,/10.00,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/Nov 20,/10.00,/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/,Okt /,10/g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/,Dez /,12./g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/,Feb /,2./g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/,Jul /,7./g' parkverstoesse_2020_cleaned.csv
sed -i '' 's/,Sep /,9./g' parkverstoesse_2020_cleaned.csv
```

4. Daten nach Spalte tatort sortieren, so dass gleichnamige Straßen/Hausnummern direkt aufeinander folgen. Dies beschleuunigt die Geokodierung, da Geokodierungsergebnisse per least-recently-used cache gecached werden können.

```sh 
csvsort -c Tatort parkverstoesse_2020_cleaned.csv > parkverstoesse_2020_sorted.csv
```
