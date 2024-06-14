import time
import math
import requests
import re
import json as js
import functools

from Helpers.Random import Random
from Networking.SocketManager import SocketManager
from Models.PlayerData import PlayerData
from Models.CharData import CharData
import Helpers.Servers as ServersHelper
import Data.MoveRecord as MoveRecord
import Networking.PacketHelper as PacketHelper
from Client.PacketHookManager import PacketHookManager
from Networking.PacketHelper import createPacket
from Helpers.RepeatTimer import RepeatTimer
from Constants.Constants import Constants

MINSPEED = 0.004
MAXSPEED = 0.0096

MINFREQ = 0.0015
MAXFREQ = 0.008

phm=PacketHookManager()
def hook(packetType):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        phm.addHook(packetType.upper(), wrapper)
        return wrapper
    return decorator

class Client:
    def __init__(self,constants:Constants):
        global phm
        self.constants = constants
        self.guid = ""
        self.password = ""
        self.secret = ""
        self.alias = ""
        self.server = ""
        self.proxy = {}
        self.proxies = {}
        self.internalServer = {"host": "", "name": ""}
        self.nexusServer = {"host": "", "name": ""}
        self.pos = None
        self.sockMan = None
        self.clientManager = None
        self.nextPos = []
        self.objectId = -1
        self.connectedTime = -1
        self.random = Random()
        self.frameTimeUpdater = None
        self.active = True
        self.isReady = False
        self.key = []
        self.keyTime = -1
        self.connectionGuid = ""
        self.gameId = self.constants.gameIds.get("nexus")
        self.buildVersion = constants.gameVersion
        self.clientToken = ""
        self.accessToken = ""
        self.playerData = PlayerData(self.constants)
        self.charData = CharData()
        self.needsNewChar = False
        self.bulletId = 0
        self.lastAttackTime = 0
        self.records = []
        self.connectCooldown = 0
        self.lastPacketTime = 0
        self.tiles = []
        self.newObjs = []
        self.drops = []
        self.phm: PacketHookManager = phm
        self.phm.addClass(self) #change this bogus

    def getToken(self, accInfo):
        self.guid = accInfo["guid"]
        self.password = accInfo["password"]
        self.secret = accInfo["secret"]
        self.alias = accInfo["alias"]
        self.proxy = accInfo.get("proxy", {})

        print("Getting token...")
        #Get access token
        r = requests.post(self.constants.apiPoints_VERIFY, data={"guid": self.guid,
                                                  "password": self.password,
                                                  "clientToken": self.clientToken,
                                                  "game_net": "Unity", "play_platform": "Unity", "game_net_user_id": ""}, headers=self.constants.apiPoints_launcherHeaders, proxies=self.proxies)
        pattern = r"AccessToken>(.+)</AccessToken>"
        try:
            self.accessToken = re.findall(pattern, r.text)[0]
        except IndexError:#Token not working
            print("GETTING TOKEN ERROR:", r.text)
            self.active = False
            return
        #Verify token
        r = requests.post(self.constants.apiPoints_VERIFYTOKEN, data={"clientToken": self.clientToken,
                                                       "accessToken": self.accessToken,
                                                       "game_net": "Unity", "play_platform": "Unity", "game_net_user_id": ""}, headers=self.constants.apiPoints_launcherHeaders, proxies=self.proxies)
        if not "Success" in r.text:
            print("VERIFYING TOKEN ERROR:", r.text)
            self.active = False
            return

    def checkInfo(self, accInfo, updateServers=False):
        if not self.active:
            return

        self.guid = accInfo["guid"]
        self.password = accInfo["password"]
        self.secret = accInfo["secret"]
        self.alias = accInfo["alias"]
        self.proxy = accInfo.get("proxy", {})

        #Get char data
        r = requests.post(self.constants.apiPoints_CHAR, data={"do_login": "true",
                                                "accessToken": self.accessToken,
                                                "game_net": "Unity", "play_platform": "Unity", "game_net_user_id": ""}, headers=self.constants.apiPoints_launcherHeaders, proxies=self.proxies)
        while "Account in use" in r.text:
            print(self.guid, "has account in use")
            try:
                time.sleep(int(re.findall(r"(\d+)", r.text)[0]))
            except IndexError:
                time.sleep(600)
            r = requests.post(self.constants.apiPoints_CHAR, data={"do_login": "true",
                                                    "accessToken": self.accessToken,
                                                    "game_net": "Unity", "play_platform": "Unity", "game_net_user_id": ""}, headers=self.constants.apiPoints_launcherHeaders, proxies=self.proxies)
        if "Account credentials not valid" in r.text:
            print(self.guid, "got invalid credentials")
            self.active = False
            return
        try:
            charInfo = re.findall(r'<Chars nextCharId="(\d+)" maxNumChars="(\d+)">', r.text)[0]
            chars = re.findall(r'<Char id="(\d+)">', r.text)
        except IndexError:
            print(r.text)
            self.active = False
            return
        
        self.charData.nextCharId = int(charInfo[0])
        self.charData.maxNumChars = int(charInfo[1])
        if len(chars) > 0:
            self.charData.charIds = [int(i) for i in chars]
            self.charData.currentCharId = int(chars[0])
        else:
            self.charData.charIds = [self.charData.nextCharId]
            self.charData.currentCharId = self.charData.nextCharId
            self.charData.nextCharId += 1
            self.needsNewChar = True
        
        if not "TDone" in r.text:
            self.gameId = self.constants.gameIds.get("tutorial")
            
        self.isReady = True

        try:
            if updateServers:
                ServersHelper.update(self.accessToken, self.proxies)
                print("Updated servers")
        except AttributeError as e:
            print("Failed to update servers")
            print(e)
            self.active = False
            self.isReady = False

    def setup(self, accInfo):
        self.server = accInfo["server"]
        self.connectedTime = int(time.time()*1000)
        
        self.internalServer = {"host": self.constants.nameToIp.get(self.server),
                               "name": self.server}
        self.nexusServer = {"host":  self.constants.nameToIp.get(self.server),
                            "name": self.server}
        
        self.sockMan = SocketManager(self.constants)
        self.sockMan.clientHook = self.onPacket
    
    def isConnected(self):
        return self.sockMan.connected

    def connect(self):
        if not self.active:
            return
        if self.connectCooldown > self.getTime():
            return
        if self.sockMan.connected:
            self.sockMan.disconnect()
        if not self.frameTimeUpdater is None:
            self.frameTimeUpdater.cancel()
        self.sockMan.connect(self.internalServer["host"], self.proxy)
        self.sendHelloPacket()

    def changeServer(self, server):
        if not server in  self.constants.nameToIp.keys():
            print(server, "is not a valid server")
            return
        self.server = server
        self.internalServer = {"host": self.constants.nameToIp[self.server],
                               "name": self.server}
        self.nexusServer = {"host": self.constants.nameToIp[self.server],
                            "name": self.server}
        self.connect()

    def getSpeed(self, time):
        if self.hasEffect(self.constants.ConditionEffects.get("SLOWED")):
            return MINSPEED
        speed = MINSPEED + (self.playerData.SPEEDSTAT+self.playerData.SPEEDBOOSTSTAT)/75 * (MAXSPEED-MINSPEED)
        if self.hasEffect(self.constants.ConditionEffects.get("SPEEDY"), self.constants.ConditionEffects.get("NINJASPEEDY")):
            speed *= 1.5
        return speed * time
    
    def nexus(self):
        packet = PacketHelper.createPacket("ESCAPE")
        self.send(packet)
        self.gameId = self.constants.gameIds.get("nexus")
        self.key = []
        self.keyTime = -1

    def sendHelloPacket(self):
        hello_packet = PacketHelper.createPacket("HELLO")
        hello_packet.buildVersion = self.buildVersion
        hello_packet.gameId = self.gameId
        hello_packet.accessToken = self.accessToken
        hello_packet.keyTime = self.keyTime
        hello_packet.key = self.key
        hello_packet.userPlatform = "rotmg"
        hello_packet.playPlatform = "rotmg"
        hello_packet.userToken = self.clientToken
        self.send(hello_packet)

    def send(self, packet):
        if self.isConnected():
            self.sockMan.sendPacket(packet)

    def getTime(self):
        return int(time.time()*1000) - self.connectedTime

    def disconnect(self):
        if self.sockMan.connected:
            self.sockMan.disconnect()
        if not self.frameTimeUpdater is None:
            self.frameTimeUpdater.cancel()
        #Wait half a sec to have less chance of getting a failure packet
        self.connectCooldown = self.getTime() + 500

    def stop(self):
        self.active = False
        if self.sockMan.connected:
            self.sockMan.disconnect()
        self.sockMan.active = False
        if not self.frameTimeUpdater is None:
            self.frameTimeUpdater.cancel()

    def updateFrameTime(self):
        if self.pos is None:
            return
        time = self.getTime()
        if len(self.nextPos) > 0:
            diff = min(100, time-self.lastFrameTime)
            self.moveTo(self.nextPos[0], diff)
        self.records.append(MoveRecord.MoveRecord(time, self.pos.x, self.pos.y))
        self.lastFrameTime = time

    def moveTo(self, target, time):
        speed = self.getSpeed(time)
        if self.pos.dist(target) > speed:
            angle = math.atan2(target.y-self.pos.y, target.x-self.pos.x)
            self.walkTo(self.pos + (math.cos(angle) * speed, math.sin(angle) * speed))
        else:
            self.walkTo(target)
            self.nextPos.pop(0)

    def walkTo(self, target):
        if self.hasEffect(self.constants.ConditionEffects.get("PARALYZED"), self.constants.ConditionEffects.get("PAUSED"), self.constants.ConditionEffects.get("PETRIFIED")):
            return
        self.pos = target.clone()

    def attackFreq(self):
        if self.hasEffect(self.constants.ConditionEffects.get("DAZED")):
            return MINFREQ
        freq = MINFREQ + (self.playerData.DEXTERITYSTAT+self.playerData.DEXTERITYBOOSTSTAT)/75 * (MAXFREQ - MINFREQ)
        if self.hasEffect(self.constants.ConditionEffects.get("BERSERK")):
            freq *= 1.5
        return freq

    def getBulletId(self):
        bulletId = self.bulletId
        self.bulletId = (self.bulletId + 1) % 128
        return bulletId

    def shoot(self, angle):
        if self.clientManager.weapons is None:
            print("Weapons not loaded")
            return False
        if self.hasEffect(self.constants.ConditionEffects.get("STUNNED"), self.constants.ConditionEffects.get("PAUSED"), self.constants.ConditionEffects.get("PETRIFIED")):
            return False
        if not self.playerData.INV[0] in self.clientManager.weapons.keys():
            return False
        time = self.getTime()
        attackPeriod = 1 / self.attackFreq() * (1/1)#TODO
        if time < self.lastAttackTime + attackPeriod:
            return False
        self.lastAttackTime = time

        shootPacket = PacketHelper.createPacket("PLAYERSHOOT")
        shootPacket.time = time
        shootPacket.containerType = self.playerData.INV[0]
        shootPacket.speedMult = self.playerData.PROJSPEEDMULT
        shootPacket.lifeMult = self.playerData.PROJLIFEMULT

        weapon = self.clientManager.weapons[shootPacket.containerType]
        arcRads = weapon.arcGap * math.pi / 180
        totalArc = arcRads * (weapon.numProjectiles - 1)
        if totalArc < 0:
            totalArc = 0
        angle -= totalArc/2

        for i in range(weapon.numProjectiles):
            shootPacket.bulletId = self.getBulletId()
            shootPacket.pos = self.pos.clone()
            shootPacket.pos.x += math.cos(angle) * 0.3
            shootPacket.pos.y += math.sin(angle) * 0.3
            shootPacket.angle = angle
            if arcRads > 0:
                angle += arcRads
            self.send(shootPacket)
            
        return True

    def hasEffect(self, *effects):
        bits = 0
        for effect in effects:
            bits |= 1 << (effect - 1)
        return (self.playerData.CONDITIONSTAT & bits) != 0
    
    @hook("createSuccess")
    def onCreateSuccess(self, packet):
        self.objectId = packet.objectId
        self.lastAttackTime = 0
        print(packet.charId)
        print(packet.PCStats)
        self.lastFrameTime = self.getTime()
        self.frameTimeUpdater = RepeatTimer(1/10, self.updateFrameTime)
        self.frameTimeUpdater.daemon = True
        self.frameTimeUpdater.start()
        self.records = []

        show_packet = PacketHelper.createPacket("SHOWALLYSHOOT")
        show_packet.toggle = 1
        self.send(show_packet)
    
    @hook("goto")
    def onGoto(self, packet):
        gotoAck_packet = PacketHelper.createPacket("GOTOACK")
        gotoAck_packet.time = self.lastFrameTime
        self.send(gotoAck_packet)
        if packet.objectId == self.objectId:
            self.pos = packet.pos.clone()

    @hook("mapInfo")
    def onMapInfo(self, packet):
        print("Connected to", self.nexusServer["name"], packet.name)
        self.nextPos = []
        if self.needsNewChar:
            print("Creating new char")
            create_packet = PacketHelper.createPacket("CREATE")
            create_packet.classType = self.constants.CharacterClasses.get("WIZZARD")
            create_packet.skinType = 0
            create_packet.isChallenger = 0
            self.send(create_packet)
            self.needsNewChar = False
        else:
            load_packet = PacketHelper.createPacket("LOAD")
            load_packet.charId = self.charData.currentCharId
            self.send(load_packet)
        self.random.setSeed(packet.seed)
        
    @hook("queueInformation")
    def onQueueInformation(self, packet):
        print("Client", self.alias, f"in queue at position: {packet.curPos}/{packet.maxPos}")
        self.connectCooldown = self.getTime() + 10*1000

    @hook("failure")
    def onFailure(self, packet):
        if packet.errorId == 15:
            self.disconnect()
            return
        print("Error:", packet.errorId)
        print(packet.errorDescription)
        self.keyTime = -1
        self.key = []
        self.gameId = self.constants.gameIds.get("nexus")
        if packet.errorDescription == "s.update_client":
            self.stop()
        elif packet.errorDescription == "Account credentials not valid":
            self.stop()
        elif packet.errorDescription == "Bad message received":
            self.disconnect()
        
    @hook("ping")
    def onPing(self, packet):
        pong_packet = PacketHelper.createPacket("PONG")
        pong_packet.serial = packet.serial
        pong_packet.time = self.getTime()
        self.send(pong_packet)

    @hook("newTick")
    def onNewTick(self, packet):
        move_packet = PacketHelper.createPacket("MOVE")
        move_packet.tickId = packet.tickId
        move_packet.time = packet.serverRealTimeMS
        move_packet.records = self.records
        if len(move_packet.records) == 0:#Causes dc otherwise
            move_packet.records = [MoveRecord.MoveRecord(self.lastFrameTime, self.pos.x, self.pos.y)]
        self.records = []
        self.send(move_packet)
        for status in packet.statuses:
            if status.objectId == self.objectId:
                self.playerData.parseStats(status.stats)

    @hook("update")
    def onUpdate(self, packet):
        if self.pos is None:
            self.pos = packet.pos
        updateAck_packet = PacketHelper.createPacket("UPDATEACK")
        self.send(updateAck_packet)
        self.tiles += packet.tiles
        self.newObjs += packet.newObjs
        self.drops += packet.drops

        for obj in packet.newObjs:
            if obj.status.objectId == self.objectId:
                self.pos = obj.status.pos
                self.playerData.parse(obj)
                

    @hook("serverPlayerShoot")
    def onServerPlayerShoot(self, packet):
        if packet.ownerId == self.objectId:
            shootAck = PacketHelper.createPacket("SHOOTACK")
            shootAck.time = self.lastFrameTime
            self.send(shootAck)

    @hook("enemyShoot")
    def onEnemyShoot(self, packet):
        shootAck = PacketHelper.createPacket("SHOOTACK")
        shootAck.time = self.lastFrameTime
        self.send(shootAck)

    @hook("reconnect")
    def onReconnect(self, packet):
        if packet.host != "":
            self.internalServer["host"] = packet.host
        if packet.name != "":
            self.internalServer["name"] = packet.name
        self.gameId = packet.gameId
        self.key = packet.key
        self.keyTime = packet.keyTime
        #self.disconnect()
        self.connect()

    def onPacket(self, packet):
        self.lastPacketTime = self.getTime()
        #print(packet.type)
        self.phm.callHooks(self, packet)

    def enterVault(self):
        vaultPortal = None
        for obj in self.newObjs:
            if obj.objectType == 1824:
                print("Vault portal found")
                vaultPortal = obj
                break

        if vaultPortal:
            if self.pos.dist(vaultPortal.status.pos) >= 0.25:
                self.nextPos = [vaultPortal.status.pos]
                print("Moving towards vault portal")
                time.sleep(2)

            # Once close enough, use the portal
            usePortal = createPacket("USEPORTAL")
            usePortal.objectId = vaultPortal.status.objectId
            self.send(usePortal)
            print("Entered vault portal")
            self.tiles = []
            self.newObjs = []
            self.drops = []
            return True
        return False

    def to_json(self):
        default = lambda o: f"<<non-serializable: {type(o).__qualname__}>>"
        json = js.dumps(self.__dict__,default=default, skipkeys=True, ensure_ascii=True,check_circular=True,indent=4)
        json_dict = js.loads(json)
        print(type(json_dict))
        json_dict["charData"] = js.loads(js.dumps(self.charData.__dict__,default=default,skipkeys=True, ensure_ascii=True,check_circular=True,indent=4))
        json_dict["playerData"] = js.loads(js.dumps(self.playerData.__dict__,default=default,skipkeys=True, ensure_ascii=True,check_circular=True,indent=4))
        json_dict["tiles"] = []
        for item in self.tiles:
            json_dict["tiles"].append(js.loads(js.dumps(item.__dict__,default=default)))
        json_dict["newObjs"] = []
        for item in self.newObjs:
            objs_json=js.loads(js.dumps(item.__dict__,default=default))
            objs_json["status"]= js.loads(js.dumps(item.status.__dict__,default=default))
            objs_json["status"]["pos"] = js.loads(js.dumps(item.status.pos.__dict__,default=default))
            objs_json["status"]["stats"] = []
            for stat in item.status.stats:
                objs_json["status"]["stats"].append(js.loads(js.dumps(stat.__dict__,default=default)))
            json_dict["newObjs"].append(objs_json)
        return json_dict