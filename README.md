# OWI-Geocoder - Ordnungswidrigkeiten verorten

## Hintergrund

## Voraussetzungen

### Daten
Voraussetzung für die Verortung ist ein durch die Kommune bereitgestellter Datensatz.
Manche Kommunen bieten diese bereits proaktiv über ein Datenportal als offene Daten an, wie z.B. [Aachen](https://offenedaten.aachen.de/dataset/verwarn-und-bussgelder-ruhender-verkehr-parkverstoesse-2021-der-stadt-aachen), [Moers](https://opendata.ruhr/dataset/bubgelder-ruhender-verkehr-moers-2020) Köln. Typische Suchbegriffe für die Suche in Portalen sind z.B. "Ruhender Verkehr", "Parkverstöße", "Ordnungswidrigkeiten". 
Für andere Kommunen müssen diese Daten gegebenenfalls erst mit einer IFG-Anfrage, wie z.B. in diesem Beispiel für die [Bußgelddaten des ruhenden Verkehrs Stuttgart](https://fragdenstaat.de/anfrage/bugelddaten-des-ruhenden-verkehrs-fur-stuttgart/), erfragt werden. (TODO: Musteranfrage)

### Tools
Erste Auswertungen (z.B. Statistiken nach Tatbestandnummer, Datum etc.) lassen sich mit Werkzeugen wie Excel vornehmen.

Für weiterführende Auswertungen, wie die von uns beabsichtigte Verortung, nutzen wir ein Python-Skript und benötigen deshalb eine lokal installierte Python-Umgebung. Für Windows. Zum lokalen Arbeiten sollte dieses Projekt ausgecheckt oder heruntergeladen werden.

Mit den folgenden Befehlen (ausgeführt im Projektverzeichnis) legen wir eine virtuelle Umgebung an und installieren die benötigten Python-Bibliotheken.

: 
```sh
# Optional: Vituelle Umgebung einrichten
$ mkvirtualenv owi-geocoder
# Benötigte Python-Bibliotheken installieren
$ pip install -r requirements.txt

```

```
## Aufruf

```sh
python3 owi-geocoder -i <input file>

```

### Datenvorbereitung
Die Daten zu Ordnungswidrigkeiten werden in sehr unterschiedlicher Form bereitgestellt. 

Für die Verortung setzen wir ein Format nach folgendem Muster voraus:

Um die Daten für die weitere Verarbeitung in dieses Format zu bringen, haben wir einige [Datenaufbereitungsbeispiele](docs/datenaufbereitung.md) beschrieben.


## Geokodierung

Im Rahmen der Geokodierung werden den textuell erfassten Tatorten Koordinaten zugewiesen.
Das Skript geocode_owis.py geht hierbei für jede Zeile wie folgt vor:
1. Parsen des Tatorts um Typ der Ortsangabe (z.B. Adresse, Kreuzung, Parkscheinautomat etc) zu ermitteln, einzelne Komponenten der Ortsangabe zu bestimmen und die Verortung behindernde Füllwörter (z.B. neben, höhe, ecke, ggü. etc.) beseitigen.
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




