from app.history import CallHistory
from app.eventbus import EVENT_BUS


class CallManager:

    def __init__(self):

        self.history = CallHistory(30)

        # Mehrere gleichzeitig aktive Anrufe
        self.current_calls = {}


    def add_call(self, call):

        call_id = call.get("id")


        # --------------------------------------------------
        # Aktuellen Anruf verwalten
        # --------------------------------------------------

        if call.get("event") == "DISCONNECT":

            if call_id is not None:

                self.current_calls.pop(
                    call_id,
                    None
                )

        else:

            if call_id is not None:

                self.current_calls[call_id] = call


        # --------------------------------------------------
        # Immer live an Browser senden
        # --------------------------------------------------

        EVENT_BUS.publish(
            call
        )


        # --------------------------------------------------
        # Nur abgeschlossene Gespräche speichern
        # --------------------------------------------------

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

        return list(
            self.current_calls.values()
        )


    def get_history(self):

        return self.history.get_all()
