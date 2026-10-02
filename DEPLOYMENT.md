# Update auf dem Ubuntu-Server

Der neue Stand liegt auf `feat/dashboard-2026`. Der Originalstand auf `main`
bleibt unverändert. Die Serverdateien `config.yaml` und `docker-compose.yml`
werden auf diesem Branch nicht verändert.

## Erstes Update

Diesen Block auf Ubuntu ausführen. Die laufende Anwendung bleibt während des
Builds erreichbar; beim Neuerstellen des Containers entsteht eine kurze
Unterbrechung. Möglichst aktualisieren, wenn kein Gespräch aktiv ist.

```bash
bash <<'UPDATE'
set -euo pipefail
cd /opt/containers/fritz-call

backup_dir="$HOME/fritz-call-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 "$backup_dir"
cp -p config.yaml docker-compose.yml "$backup_dir/"
if [ -f .env ]; then cp -p .env "$backup_dir/"; fi
git rev-parse HEAD > "$backup_dir/commit.txt"

# Den tatsächlich laufenden Originalstand sichern, auch wenn das Image-Tag abweicht.
if ! docker image inspect fritz-call:original-20261002 >/dev/null 2>&1; then
  original_image=$(docker inspect --format '{{.Image}}' fritz-call)
  docker image tag "$original_image" fritz-call:original-20261002
fi

git fetch origin
git switch --track origin/feat/dashboard-2026
docker compose config --quiet
docker build -t fritz-call:dashboard-20261002 .
docker image tag fritz-call:dashboard-20261002 fritz-call:latest
docker compose up -d --no-deps --force-recreate fritz-call
docker compose ps fritz-call
docker compose logs --tail=50 fritz-call
printf '\nKonfiguration gesichert unter: %s\n' "$backup_dir"
UPDATE
```

Bei einem Fehler bricht der Block ab. Der Branchwechsel schützt vor dem
Überschreiben konfliktbehafteter lokaler Änderungen. Kein `git reset --hard`
verwenden. Der Block ist für den ersten Wechsel von `main` gedacht.

Danach die Telefonoberfläche mit `Strg+F5` neu laden. Prüfen:

- Webserver und FRITZ!Box werden getrennt als verbunden angezeigt.
- Der Kundenexport ist verfügbar; ein fehlgeschlagener SMB-Abgleich erscheint als Hinweis.
- Ein Testanruf wird beim Klingeln und bei Gesprächsannahme angezeigt und nach
  Gesprächsende korrekt in der Historie gespeichert.
- Desktop- und Mobilansicht sowie Benachrichtigungen prüfen.

## Sofort zum Original zurück

Das gesicherte Image enthält den alten Code und die alte Oberfläche. Für den
Rückweg ist kein neuer Build erforderlich:

```bash
bash <<'ROLLBACK'
set -euo pipefail
cd /opt/containers/fritz-call
docker image tag fritz-call:original-20261002 fritz-call:latest
docker compose up -d --no-deps --force-recreate fritz-call
git switch main
docker compose ps fritz-call
ROLLBACK
```

Die lokale Konfiguration und `data` bleiben erhalten. Die neue SQLite-Datei wird
vom Original ignoriert. Die bisherige, ausschließlich im Arbeitsspeicher
gehaltene Anrufhistorie kann beim Containerwechsel nicht übernommen werden.
