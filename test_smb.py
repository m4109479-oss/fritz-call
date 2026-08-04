import os
import smbclient


server = "192.168.100.250"

username = os.getenv("SMB_USERNAME")
password = os.getenv("SMB_PASSWORD")


smbclient.register_session(
    server,
    username=username,
    password=password
)


path = r"\\192.168.100.250\PlusFakt"

print("Teste Zugriff auf:")
print(path)

print(smbclient.listdir(path))

print("SMB Zugriff OK")
