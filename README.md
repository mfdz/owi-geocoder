# Geocoding

## Datenaufbereitung

1. Aus Datei "Halt undd Parkverstöße Stuttgart.xlsx" Tabellenblatt 2020 als parkverstoesse_2020.csv exportieren
2. Mittels `tail -n+5 parkverstoesse_2020.csv > parkverstoesse_2020_.csv` Kopfzeilen entfernen
3. Datums-/Zeitfelder bereinigen (erfordert installiertes [cvskit](https://csvkit.readthedocs.io/en/latest/))
```sh
paste -d, \
    <( csvcut -c 1 -d ';' parkverstoesse_2020_.csv ) \
    <( csvcut -c 2 -d ';' parkverstoesse_2020_.csv | cut -c1-10 ) \
    <( csvcut -c 3 -d ';' parkverstoesse_2020_.csv | cut -c12-19 | tail -n+2 | sed 's/^/Tatzeit\n/') \
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

`csvsort -c tatort parkverstoesse_2020_cleaned.csv > parkverstoesse_2020_sorted.csv

## Geokodierung

Im Rahmen der Geokodierung werden den textuell erfassten Tatorten Koordinaten zugewiesen.
Das Skript geocode_owis.py geht hierbei für jede Zeile wie folgt vor:
1. Parsen des Tatorts um Typ der Ortsangabe (z.B. Adresse, Kreuzung, Parkscheinautomat etc) zu ermitteln, einzelne Komponenten zu bestimmen und die Verortung behindernde Füllwörter (z.B. neben, höhe, ecke, ggü. etc.) beseitigen.
2. Verorten der Parkscheinautomaten anhand PSA-Nr / Straße
3. Verorten der Adresse (im ersten Versuch mit Hnr, im zweiten ohne)
4. Weitere Veortungsotionen stehen noch aus:
  [ ] Parkplätze/-häuser
  [ ] Straßenkreuzungen
  [ ] Lichtmasten (niedrige Prio)
  [ ] Wendeplatz (niedrige Prio)

Zur Geokodierung von Adressen wird über die Bibliothek geopy mit Photon durchgeführt. Die aktuelle Version unterstützt noch nicht die Vorgabe einer BoundingBox, weshalb das Projekt die entsprechend gepatchte Datei enthält.

Zur Geokodierung von Parkscheinautomaten wird die Bibliothek osmnx genutzt.

Zum Ausführen müssen erst die  Abhängigkeiten installiert werden (unter Windows ggf. abweichend )
1. `pip install -r requirements`
2. `GEOCODER_DOMAIN=photon.domain.xyz python geocoder_owis.py`, wobei photon.domain.xyz durch eine konkreten Service-Host zu ersetzen ist (bei Holger erfragen)



