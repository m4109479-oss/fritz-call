from app.history import CallHistory
from app.eventbus import EVENT_BUS


class CallManager:

    def __init__(self):

        self.history = CallHistory(30)
        self.current_call = None


    def add_call(self, call):

        self.current_call = call


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


    def get_current(self):

        return self.current_call


    def get_history(self):

        return self.history.get_all()
