from collections import deque


class CallHistory:

    def __init__(self, size=30):
        self.calls = deque(maxlen=size)


    def add(self, call):

        self.calls.appendleft(call)


    def get_all(self):

        return list(self.calls)
