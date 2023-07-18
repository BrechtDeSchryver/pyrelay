class TradeRequestedPacket:
    def __init__(self):
        self.type = "TRADEREQUESTED"
        self.send = True
        self.name = ""

    def read(self, reader):
        self.name = reader.readStr()

    def write(self, writer):
        writer.writeStr(self.name)
