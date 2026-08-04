import socket
import time

from app.eventbus import EVENT_BUS


class FritzBoxListener:

    def __init__(self, call_manager, customer_lookup, host, port):

        self.call_manager = call_manager
        self.customer_lookup = customer_lookup

        self.host = host
        self.port = port

        self.active_call = None


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

            result["number"] = parts[3]
            result["target"] = parts[4]


        elif event == "CONNECT":

            result["id"] = parts[3]


        elif event == "DISCONNECT":

            result["duration"] = parts[3]


        return result



    def handle_event(self, event):

        if event["event"] == "RING":

            event["customer"] = self.customer_lookup.find(
                event["number"]
            )

            self.active_call = event


            # RING speichern und live senden
            self.call_manager.add_call(
                event
            )


        elif event["event"] == "CONNECT":

            if self.active_call:

                connect_call = self.active_call.copy()

                connect_call["event"] = "CONNECT"
                connect_call["id"] = event.get("id")


                # nur live senden, nicht Historie
                EVENT_BUS.publish(
                    connect_call
                )



        elif event["event"] == "DISCONNECT":

            if self.active_call:

                self.active_call["duration"] = int(
                    event.get("duration", 0)
                )


                self.active_call["event"] = "DISCONNECT"


                self.call_manager.add_call(
                    self.active_call
                )


                print(
                    "Gespeichert:",
                    self.active_call
                )


                self.active_call = None



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
