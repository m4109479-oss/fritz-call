from app.history import CallHistory
from app.eventbus import EVENT_BUS


class CallManager:

    def __init__(self):

        self.history = CallHistory(30)

        # mehrere aktive Gespräche
        self.current_calls = {}


    def add_call(self, call):

        call_id = call.get("id")


        # Live-Zustand verwalten
        if call.get("event") in [
            "RING",
            "CONNECT"
        ]:

            if call_id:

                self.current_calls[call_id] = call



        # immer live an Browser senden
        EVENT_BUS.publish(
            call
        )



        # nur abgeschlossene Gespräche speichern
        if call.get("event") != "DISCONNECT":

            return



        duration = int(
            call.get("duration", 0)
        )


        call["duration"] = duration


        if duration == 0:

            call["status"] = "missed"

        else:

            call["status"] = "answered"



        self.history.add(
            call
        )


        # aktiven Call entfernen
        if call_id in self.current_calls:

            del self.current_calls[call_id]



    def get_current(self):

        return self.current_calls


    def get_history(self):

        return self.history.get_all()
