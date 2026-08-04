import csv
import os
import re


class CustomerLookup:

    def __init__(self, filename):
        self.filename = filename
        self.customers = {}
        self.last_modified = 0

        self.reload()


    def normalize_phone(self, number):

        if not number:
            return ""

        number = re.sub(r"\D", "", number)

        if number.startswith("49"):
            number = "0" + number[2:]

        if len(number) < 5 or len(number) > 15:
            return ""

        return number



    def reload(self):

        customers = {}

        with open(
            self.filename,
            encoding="utf-8-sig"
        ) as file:


            reader = csv.DictReader(
                file,
                delimiter=";"
            )


            for row in reader:


                lastname = (
                    row.get("Zuname", "")
                    .strip()
                )


                firstname = (
                    row.get("Vorname", "")
                    .strip()
                )


                if not lastname:
                    continue



                if firstname:

                    name = (
                        lastname
                        + ", "
                        + firstname
                    )

                else:

                    name = lastname



                for field in [

                    "Telefon1",
                    "Telefon2",
                    "TelefonMobil1",
                    "TelefonMobil2"

                ]:


                    number = self.normalize_phone(

                        row.get(field)

                    )


                    if number:

                        customers[number] = name



        self.customers = customers


        self.last_modified = os.path.getmtime(

            self.filename

        )


        print(
            f"CSV geladen: {len(customers)} Nummern"
        )




    def check_reload(self):

        modified = os.path.getmtime(

            self.filename

        )


        if modified != self.last_modified:

            print(
                "CSV geändert - lade neu"
            )

            self.reload()




    def find(self, number):

        self.check_reload()


        number = self.normalize_phone(number)


        return self.customers.get(

            number,

            "unbekannt"

        )
