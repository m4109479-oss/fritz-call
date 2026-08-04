class EventBus:

    def __init__(self):

        self.subscribers = []


    def subscribe(self, callback):

        self.subscribers.append(
            callback
        )


    def unsubscribe(self, callback):

        if callback in self.subscribers:

            self.subscribers.remove(
                callback
            )


    def publish(self, event):

        for callback in self.subscribers.copy():

            try:

                callback(event)

            except Exception as e:

                print(
                    "EventBus Fehler:",
                    e
                )


EVENT_BUS = EventBus()
