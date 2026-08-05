import socket
import time

from app.eventbus import EVENT_BUS


class FritzBoxListener:

    def __init__(self, call_manager, customer_lookup, host, port):

        self.call_manager = call_manager
        self.customer_lookup = customer_lookup

        self.host = host
        self.port = port

        # mehrere gleichzeitige Gespräche möglich
        # Schlüssel ist die FRITZ!Box Call-ID
        self.active_calls = {}


    def parse_event(self, line):

        parts = line.strip().split(";")

        if len(parts) < 3:
            return None


        event = parts[1]
        call_id = parts[2]


        result = {
            "time": parts[0],
            "event": event,
            "id": call_id
        }


        if event == "RING":

            result["number"] = parts[3]
            result["target"] = parts[4]


        elif event == "CONNECT":

            # CONNECT enthält die Nebenstelle
            if len(parts) > 3:
                result["target"] = parts[3]


        elif event == "DISCONNECT":

            result["duration"] = parts[3]


        return result



    def handle_event(self, event):

        event_type = event["event"]
        call_id = event.get("id")


        if event_type == "RING":

            event["customer"] = self.customer_lookup.find(
                event["number"]
            )


            # neuen aktiven Anruf speichern
            self.active_calls[call_id] = event


            # sofort live senden
            self.call_manager.add_call(
                event
            )



        elif event_type == "CONNECT":

            if call_id in self.active_calls:


                connect_call = self.active_calls[call_id].copy()

                connect_call["event"] = "CONNECT"

                connect_call["id"] = call_id


                if "target" in event:
                    connect_call["target"] = event["target"]


                # nur live senden
                EVENT_BUS.publish(
                    connect_call
                )



        elif event_type == "DISCONNECT":

            if call_id in self.active_calls:


                call = self.active_calls[call_id]


                call["event"] = "DISCONNECT"


                call["duration"] = int(
                    event.get("duration", 0)
                )


                self.call_manager.add_call(
                    call
                )


                print(
                    "Gespeichert:",
                    call
                )


                # nur diesen Anruf entfernen
                del self.active_calls[call_id]



        print(event)



    def start(self):

        while True:

            sock = None

            try:

                print(
                    "Verbinde mit FRITZ!Box..."
                )


                sock = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_STREAM
                )


                sock.connect(
                    (
                        self.host,
                        self.port
                    )
                )


                print(
                    "Verbunden."
                )


                buffer = ""


                while True:

                    data = sock.recv(
                        1024
                    )


                    if not data:

                        raise ConnectionError(
                            "FRITZ!Box Verbindung geschlossen"
                        )


                    buffer += data.decode(
                        "utf-8"
                    )


                    while "\n" in buffer:

                        line, buffer = buffer.split(
                            "\n",
                            1
                        )


                        event = self.parse_event(
                            line
                        )


                        if event:

                            self.handle_event(
                                event
                            )


            except Exception as e:

                print(
                    "FRITZ!Box Fehler:",
                    e
                )


            finally:

                if sock:

                    try:
                        sock.close()

                    except:
                        pass


            print(
                "Neuer Verbindungsversuch in 5 Sekunden..."
            )


            time.sleep(5)
