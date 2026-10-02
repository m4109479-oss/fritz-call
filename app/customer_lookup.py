import csv
import logging
import os
import re
import threading

logger = logging.getLogger(__name__)
PHONE_FIELDS = ("Telefon1", "Telefon2", "TelefonMobil1", "TelefonMobil2")


def validate_reader(reader):
    fields = set(reader.fieldnames or [])
    if "Zuname" not in fields or not fields.intersection(PHONE_FIELDS):
        raise ValueError("CSV benötigt Zuname und mindestens eine Telefonspalte")


class CustomerLookup:
    def __init__(self, filename):
        self.filename = filename
        self.customers = {}
        self.last_modified = None
        self.lock = threading.RLock()
        self.reload()

    def normalize_phone(self, number):
        if not number:
            return ""
        number = re.sub(r"\D", "", str(number))
        if number.startswith("0049"):
            number = "0" + number[4:].lstrip("0")
        elif number.startswith("49"):
            number = "0" + number[2:].lstrip("0")
        if not 5 <= len(number) <= 15:
            return ""
        return number

    def reload(self):
        with self.lock:
            try:
                customers = {}
                with open(self.filename, encoding="utf-8-sig", newline="") as file:
                    modified = os.fstat(file.fileno()).st_mtime_ns
                    reader = csv.DictReader(file, delimiter=";")
                    validate_reader(reader)
                    for row in reader:
                        if None in row or any(value is None for value in row.values()):
                            raise ValueError("Unvollständige CSV-Zeile")
                        lastname = (row.get("Zuname") or "").strip()
                        firstname = (row.get("Vorname") or "").strip()
                        if not lastname:
                            continue
                        name = f"{lastname}, {firstname}" if firstname else lastname
                        for field in PHONE_FIELDS:
                            number = self.normalize_phone(row.get(field))
                            if number:
                                customers[number] = name
                self.customers = customers
                self.last_modified = modified
                logger.info("CSV geladen: %s Nummern", len(customers))
                return True
            except (OSError, UnicodeError, csv.Error, ValueError):
                logger.warning("Kundenexport nicht lesbar; letzter Kundenbestand bleibt erhalten")
                return False

    def check_reload(self):
        try:
            modified = os.stat(self.filename).st_mtime_ns
        except OSError:
            return
        if modified != self.last_modified:
            self.reload()

    def find(self, number):
        self.check_reload()
        with self.lock:
            return self.customers.get(self.normalize_phone(number), "unbekannt")
