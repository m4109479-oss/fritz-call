# Fritz-Call ☎

Fritz-Call ist eine kleine Docker-basierte Webanwendung zur Anzeige eingehender Telefonate über den FRITZ!Box Callmonitor.

Die Anwendung verbindet eine FRITZ!Box-IP-Telefonanlage mit einer Weboberfläche und kann Anrufer anhand eines PlusFakt-Kundenexports erkennen.

## Funktionen

* 📞 Empfang von Telefonereignissen über den FRITZ!Box Callmonitor
* 🔎 automatische Kundenerkennung über PlusFakt Exportdaten
* 🌐 Weboberfläche zur Anzeige aktueller und vergangener Anrufe
* 🔔 Browser-Benachrichtigung bei eingehenden Anrufen
* 🟠 Popup-Anzeige für eingehende Anrufe
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

## Aktueller Status

Das Projekt befindet sich in aktiver Entwicklung.

Geplante Erweiterungen:

* Unterstützung mehrerer paralleler Anrufe
* verbesserte Live-Anzeige aktiver Gespräche
* weitere Integrationen mit ERP-/CRM-Systemen

## Lizenz

Dieses Projekt wird zur privaten und betrieblichen Nutzung bereitgestellt.
