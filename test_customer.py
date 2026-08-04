from app.customer_lookup import CustomerLookup


customers = CustomerLookup(
    "Export.csv"
)


print(
    customers.find("06503/981535")
)
