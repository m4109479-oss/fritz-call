from app.history import CallHistory


history = CallHistory(3)


history.add({
    "customer": "Stückrath",
    "number": "06503981535"
})

history.add({
    "customer": "Berner GmbH",
    "number": "01715201239"
})


print(history.get_all())
