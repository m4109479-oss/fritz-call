import socket
import time

from app.eventbus import EVENT_BUS


class FritzBoxListener:

    def __init__(self, call_manager, customer_lookup, host, port):

        self.call_manager = call_manager
        self.customer_lookup = customer_lookup

        self.host = host
        self.port = port

        # Mehrere gleichzeitig aktive Anrufe
        self.active_calls = {}


    def parse_event(self, line):

        parts = line.strip().split(";")

        if len(parts) < 2:
            return None

        event = parts[1]

        result = {
            "time": parts[0],
            "event": event
        }


        if event == "RING":

            # FRITZ!Box:
            # time;RING;id;number;target;...
            if len(parts) < 5:
                return None

            result["id"] = parts[2]
            result["number"] = parts[3]
            result["target"] = parts[4]


        elif event == "CONNECT":

            # FRITZ!Box:
            # time;CONNECT;id;
            if len(parts) < 3:
                return None

            result["id"] = parts[2]


        elif event == "DISCONNECT":

            # FRITZ!Box:
            # time;DISCONNECT;id;duration;
            if len(parts) >= 4:

                result["id"] = parts[2]
                result["duration"] = parts[3]

            else:
                return None


        return result



    def handle_event(self, event):

        event_type = event["event"]


        # --------------------------------------------------
        # RING
        # --------------------------------------------------

        if event_type == "RING":

            call_id = event.get("id")

            if call_id is None:
                return


            event["customer"] = self.customer_lookup.find(
                event["number"]
            )


            # Anruf anhand der FRITZ!Box-ID speichern
            self.active_calls[call_id] = event


            # Live an Browser senden
            self.call_manager.add_call(
                event
            )


        # --------------------------------------------------
        # CONNECT
        # --------------------------------------------------

        elif event_type == "CONNECT":

            call_id = event.get("id")

            if call_id is None:
                return


            call = self.active_calls.get(
                call_id
            )


            if call:

                connect_call = call.copy()

                connect_call["event"] = "CONNECT"

                connect_call["id"] = call_id


                # Nur live senden
                EVENT_BUS.publish(
                    connect_call
                )


        # --------------------------------------------------
        # DISCONNECT
        # --------------------------------------------------

        elif event_type == "DISCONNECT":

            call_id = event.get("id")


            if call_id is None:
                return


            call = self.active_calls.pop(
                call_id,
                None
            )


            if call:

                call["duration"] = int(
                    event.get("duration", 0)
                )

                call["event"] = "DISCONNECT"


                # Abschluss speichern + live senden
                self.call_manager.add_call(
                    call
                )


                print(
                    "Gespeichert:",
                    call
                )


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
