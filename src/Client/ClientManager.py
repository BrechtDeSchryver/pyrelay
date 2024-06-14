import time
import random
from hashlib import md5

from Client.Client import Client
from Constants.Constants import Constants

class ClientManager:
    def __init__(self, constants: Constants):
        self.constants = constants
        self.clients = []
        self.updateServers = False
        self.running = True

    def addClient(self, accInfo):
        if "guid" in accInfo.keys() and "password" in accInfo.keys():
            if not "secret" in accInfo.keys():
                accInfo["secret"] = ""
            if accInfo["guid"] == "" or (accInfo["password"] == "" and accInfo["secret"] == ""):
                print("Empty email or password, skipping account")
                return None
            if not "alias" in accInfo.keys():
                accInfo["alias"] = accInfo["guid"]
            if "proxy" in accInfo.keys():
                if not "username" in accInfo["proxy"].keys():
                    accInfo["proxy"]["username"] = ""
                if not "password" in accInfo["proxy"].keys():
                    accInfo["proxy"]["password"] = ""

            for client in self.clients:
                if client.guid == accInfo["guid"]:
                    print("Account already added")
                    return None

            proxy = accInfo.get("proxy", {})
            proxies = {}
            if proxy != {}:
                proxies = {
                    "https": "socks{}://".format(proxy["type"]) +
                    ("{}:{}@".format(proxy["username"], proxy["password"]) if proxy["username"] != "" else "") +
                    "{}:{}".format(proxy["host"], proxy["port"])
                }

            client = Client(self.constants)

            client.clientToken = md5(accInfo["guid"].encode(
                "utf-8") + accInfo["password"].encode("utf-8")).hexdigest()
            client.proxies = proxies

            client.getToken(accInfo)

            client.checkInfo(accInfo, self.updateServers)


            if not "server" in accInfo.keys():
                accInfo["server"] = random.choice(
                    list(self.constants.nameToIp.keys()))
                print("Server not in account info using server",
                      accInfo["server"], "instead")
            if not accInfo["server"] in list(self.constants.nameToIp.keys()):
                old = accInfo["server"]
                accInfo["server"] = random.choice(
                    list(self.constants.nameToIp.keys()))
                print("Invalid server", old, "using server",
                      accInfo["server"], "instead")

            client.setup(accInfo)

            client.clientManager = self
            client.connect()

            self.clients.append(client)

            return client

    def getClientData(self, guid):
        for client in self.clients:
            if client.guid == guid:
                return client.to_json()
        return None

    def removeClient(self, guid):
        new_clients = []
        for client in self.clients:
            if client.guid == guid:
                client.stop()
            else:
                new_clients.append(client)
        self.clients = new_clients
        return True

    def reconnectIfNeeded(self):
        if any(client.active for client in self.clients):
            for client in self.clients:
                if client.isReady and client.active and not client.isConnected():
                    # Has client been disconnected for more than 2.5 secs?
                    if client.lastPacketTime + 2500 < client.getTime():
                        client.connect()
        elif len(self.clients):
            return True

    def stop(self):
        self.running = False
        print("Disconnecting clients...")
        for client in self.clients:
            client.stop()

    def reconnect_loop(self):
        while self.running:
            if self.reconnectIfNeeded():
                print("No clients are active - exiting")
                exit(1)
            time.sleep(0.5)

    def sendPacket(self, guid, packet):
        for client in self.clients:
            if client.guid == guid:
                client.send(packet)
                return True
        return False

    def letClientEnterVault(self, guid):
        for client in self.clients:
            if client.guid == guid:
                return client.enterVault()
        return False
