# Fritz-Call ☎

Fritz-Call ist eine kleine Docker-basierte Webanwendung zur Anzeige eingehender Telefonate über den FRITZ!Box Callmonitor.

Die Anwendung verbindet eine FRITZ!Box-IP-Telefonanlage mit einer Weboberfläche und kann Anrufer anhand eines PlusFakt-Kundenexports erkennen.

## Funktionen

* 📞 Empfang von Telefonereignissen über den FRITZ!Box Callmonitor
* 🔎 automatische Kundenerkennung über PlusFakt Exportdaten
* 🌐 Weboberfläche zur Anzeige aktueller und vergangener Anrufe
* 🔔 Browser-Benachrichtigung bei eingehenden Anrufen
* 🟠 Eigener Bereich für klingelnde und laufende Gespräche
* 🔎 Suche, Statusfilter und Zeitraumfilter für die Anrufliste
* 💾 Dauerhafte Anrufhistorie mit SQLite (standardmäßig die letzten 1000 Anrufe)
* 🟢 Getrennte Verbindungsanzeige für Webserver und FRITZ!Box
* 🐳 Betrieb als Docker-Container
* 🔄 automatischer Abgleich der PlusFakt-CSV-Datei

## Architektur

```
FRITZ!Box
    |
    | TCP Callmonitor (Port 1012)
    |
Fritz-Call Container
    |
    +-- Kundensuche
    |      |
    |      +-- PlusFakt Export.csv
    |
    +-- Weboberfläche
```

## Voraussetzungen

* Linux-Server mit Docker
* FRITZ!Box mit aktiviertem Callmonitor
* Zugriff auf den PlusFakt Export
* Browser mit Unterstützung für Web Notifications

## Installation

Repository klonen:

```bash
git clone https://github.com/m4109479-oss/fritz-call.git
cd fritz-call
```

Umgebungsvariablen anlegen:

```bash
cp .env.example .env
```

Die Datei `.env` anpassen:

```env
SMB_USERNAME=username
SMB_PASSWORD=password
```

Konfiguration anpassen:

```yaml
fritzbox:
  ip: 192.168.1.1
  port: 1012

plusfakt:
  server: 192.168.1.100
  share: PlusFakt
  path: PlusFakt Enterprise/Export/Export.csv
  refresh_hours: 2

customer:
  csv_file: /data/Export.csv
```

Container bauen:

```bash
docker build -t fritz-call .
```

Starten:

```bash
docker compose up -d
```

Die Weboberfläche ist anschließend erreichbar unter:

```
http://SERVER-IP:8000
```

## Konfiguration der FRITZ!Box

Der Callmonitor muss auf der FRITZ!Box aktiviert werden:

```
Telefon → Eigene Rufnummern → Anschlusseinstellungen
→ Unterstützung für FRITZ!Box-Kennwort aktivieren
```

Anschließend kann der Callmonitor über Port `1012` verwendet werden.

## Datenquelle PlusFakt

Fritz-Call erwartet eine CSV-Datei aus PlusFakt:

```
PlusFakt Enterprise/Export/Export.csv
```

Die Datei wird regelmäßig aktualisiert und für die Rufnummernsuche verwendet.

Unterstützte Felder:

* Zuname
* Vorname
* Telefon1
* Telefon2
* TelefonMobil1
* TelefonMobil2

## Projektstruktur

```
fritz-call/
├── app/
│   ├── api.py
│   ├── fritzbox.py
│   ├── customer_lookup.py
│   ├── call_manager.py
│   └── ...
│
├── web/
│   └── index.html
│
├── data/
│   └── Export.csv
│
├── Dockerfile
├── docker-compose.yml
└── config.yaml
```

## Dashboard und Zuverlässigkeit

Die Oberfläche zeigt abgeschlossene Anrufe als Tabelle mit festen Spalten und
auf kleinen Bildschirmen als Karten. Tageszahlen beziehen sich auf die
abgeschlossenen Anrufe in der gespeicherten Historie. Eingehende Anrufe erhalten
einen eigenen Bereich oberhalb der Liste und können Browser-Benachrichtigungen
auslösen. Die Zielrufnummer und die beim Verbinden ermittelte Nebenstelle sind
unterschiedliche Angaben.

Der CSV-Abgleich läuft im Hintergrund. Downloads werden zuerst in eine
temporäre Datei geschrieben, auf CSV-Struktur und Vollständigkeit geprüft und
erst dann atomar ersetzt. Bei Fehlern bleibt der letzte gültige Kundenbestand
erhalten; die Anwendung startet auch ohne erreichbaren SMB-Server. Ohne
verfügbaren Kundenbestand werden Anrufer als unbekannt angezeigt.

Nach einer Browser-Unterbrechung werden Live-Anzeige und Historie erneut vom
Server geladen. Bei Verlust der Callmonitor-Verbindung werden unsichere aktive
Anrufe entfernt. Während der Unterbrechung verpasste Telefonereignisse können
vom Callmonitor nicht nachträglich rekonstruiert werden und werden nicht als
abgeschlossene Anrufe erfunden.

Die Historie liegt standardmäßig neben der CSV-Datei in `calls.sqlite3`, also
bei der bestehenden Konfiguration in `/data/calls.sqlite3`. Optional:

```yaml
history:
  file: /data/calls.sqlite3
  size: 1000
```

Der Exportzeitpunkt wird regelmäßig aktualisiert; Daten älter als 48 Stunden
werden markiert. Der Zeitpunkt bezieht sich auf die Quelldatei, nicht auf den
Download. Rufnummern mit `+49`, `0049` und deutscher Inlandsschreibweise werden
einheitlich erkannt.

Die Anleitung für das bestehende Ubuntu-/Proxy-Setup einschließlich Sicherung
und Rückweg zum Original steht in [DEPLOYMENT.md](DEPLOYMENT.md). Beim ersten
Containerwechsel geht die zuvor nur im Arbeitsspeicher gehaltene Historie
verloren; neue Einträge bleiben anschließend über Neustarts erhalten.

## Tests

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
npm ci
npm test
```

Node.js wird nur für die DOM-Regressionstests benötigt, nicht im Dockerbetrieb.
Die Tests prüfen unter anderem CSV-Ausfälle, Rufnummernformate, parallele
Gespräche, Annahme bei null Sekunden, SQLite-Aufbewahrung, API/WebSocket sowie
Frontend-Filter und Wiederverbindung. DOM-Tests ersetzen keine visuelle
Browserprüfung.

## Lizenz

Dieses Projekt wird zur privaten und betrieblichen Nutzung bereitgestellt.
