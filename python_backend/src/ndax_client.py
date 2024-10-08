import json
import random
import time
import asyncio
import hmac
import hashlib
import websockets
from decimal import Decimal as dec


class NdaxConfig:
    live = False
    api_key = None
    secret = None
    user_id = None
    acct_id = None
    oms_id = None
    tkr_dct = None
    ws_api_port = None


def tkr_parser(data_list):
    data_list = [
        (
            int(col[0]),    # date_time
            dec(str(col[1])),    # high
            dec(str(col[2])),    # low
            dec(str(col[3])),    # open
            dec(str(col[4])),    # close
            dec(col[5]),    # volumne
            dec(str(col[6])),    # inside_bid_price
            dec(str(col[7])),    # inside_ask_price
            int(col[8]),    # tkr_id
            int(col[9])     # date_time_beg
        )
        for col in data_list
    ]
    return data_list


def lvl1_parser(data_dict):
    timestamp = time.time() * 1000
    data = {
        "timestamp_ms": int(timestamp),
        "tkr_id": int(data_dict["InstrumentId"]),
        "best_bid": dec(str(data_dict["BestBid"])),
        "best_ask": dec(str(data_dict["BestOffer"])),
        "last_trade_price": dec(str(data_dict["LastTradedPx"])),
        "last_trade_qty": dec(str(data_dict["LastTradedQty"])),
        "last_trade_time": int(data_dict["LastTradeTime"])
    }
    return data


class NdaxClient:
    def __init__(self, config, sender_queue, data_queue, db_queue):
        self.api_key = config.api_key
        self.secret = config.secret
        self.user_id = config.user_id
        self.acct_id = config.acct_id
        self.uri = config.uri
        self.oms_id = config.oms_id
        self.tkr_dct = config.tkr_dct
        self.sender_queue = sender_queue
        self.data_queue = data_queue
        self.db_queue = db_queue
        self.ws = None
        self.authenticated = False
        self.server_queue = asyncio.Queue(maxsize=5)
        self.server_port = config.server_port
        self.server_clients = set()

    async def authenticate(self):
        print("authenticating")

        # HMAC-Sha256 encoding
        nonce = random.randint(1000, 9999)
        message = "{}{}{}".format(nonce, self.user_id, self.api_key)
        signature = hmac.new(
            self.secret.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

        payload = {
            "APIKey": self.api_key,
            "Signature": signature,
            "UserId": str(self.user_id),
            "Nonce": str(nonce),
        }
        message = {
            "m": 0,
            "i": int(time.time()),
            "n": "AuthenticateUser",
            "o": json.dumps(payload)
        }
        await self.ws.send(json.dumps(message))

        response = await self.ws.recv()
        response = json.loads(response)
        r = json.loads(response["o"])
        if r["Authenticated"] is True:
            print("NDAX user authenticated")
            self.authenticated = True
        else:
            print("NDAX user not authenticated")
            await self.data_queue.put({"action": "quit"})

    async def get_account_pos(self):
        payload = {
            "AccountId": self.acct_id,
            "OMSId": self.oms_id
        }
        message = {
            "m": 0,
            "i": int(time.time()),
            "n": "GetAccountPositions",
            "o": json.dumps(payload)
        }
        await self.ws.send(json.dumps(message))

    async def subscribe_tkr(self):
        for tkr, _ in self.tkr_dct.items():
            print("subscribing tkr:", tkr)
            payload = {
                "OMSId": self.oms_id,
                "InstrumentId": int(tkr),
                "Interval": 60,
                "IncludeLastCount": 0
            }
            message = {
                "m": 0,
                "i": int(time.time()),
                "n": "SubscribeTicker",
                "o": json.dumps(payload),
            }
            await self.ws.send(json.dumps(message))

    async def unsubscribe_tkr(self):
        for tkr, _ in self.tkr.items():
            print("unsubscribing tkr:", tkr)
            payload = {
                "OMSId": self.oms_id,
                "InstrumentId": int(tkr),
            }
            message = {
                "m": 0,
                "i": int(time.time()),
                "n": "UnsubscribeTicker",
                "o": json.dumps(payload),
            }
            await self.ws.send(json.dumps(message))

    async def subscribe_lvl1(self):
        for tkr, _ in self.tkr_dct.items():
            print("subscribing level 1 tkr:", tkr)
            payload = {
                "OMSId": self.oms_id,
                "InstrumentId": int(tkr),
            }
            message = {
                "m": 0,
                "i": int(time.time()),
                "n": "SubscribeLevel1",
                "o": json.dumps(payload)
            }
            await self.ws.send(json.dumps(message))

    async def unsubscribe_lvl1(self):
        for tkr, _ in self.tkr_dct.items():
            print("unsubscribing level 1 tkr:", tkr)
            payload = {
                "OMSId": self.oms_id,
                "InstrumentId": int(tkr),
            }
            message = {
                "m": 0,
                "i": int(time.time()),
                "n": "UnsubscribeLevel1",
                "o": json.dumps(payload)
            }
            await self.ws.send(json.dumps(message))

    async def send_order(self, tkr_id, order_id, side, qty):
        if not self.live:
            print("sim trade")

        else:
            # Send market order
            payload = {
                "InstrumentId": tkr_id,
                "OMSId": self.oms_id,
                "AccountId": self.acct_id,
                "TimeInForce": 1,
                "ClientOrderId": order_id,
                "Side": side,
                "Quantity": qty,
                "OrderType": 1
            }
            message = {
                "m": 0,
                "i": int(time.time()),
                "n": "SendOrder",
                "o": json.dumps(payload)
            }
            await self.ws.send(json.dumps(message))

    async def logout(self):
        print("Logging out")
        message = {
            "m": 0,
            "i": int(time.time()),
            "n": "LogOut",
            "o": "{}"
        }
        await self.ws.send(json.dumps(message))

    async def start_receiver(self):
        while True:
            response = await self.ws.recv()
            response = json.loads(response)

            match response["n"]:
                case "SubscribeTicker" | "TickerDataUpdateEvent":
                    data = tkr_parser(json.loads(response["o"]))
                    await self.data_queue.put({"action": "tkr", "data": data})
                    await self.db_queue.put({"action": "tkr", "data": data})

                case "SubscribeLevel1" | "Level1UpdateEvent":
                    data = json.loads(response["o"], object_hook=lvl1_parser)
                    data["tkr"] = self.tkr_dct[str(data["tkr_id"])]
                    await self.db_queue.put({"action": "lvl1", "data": data})
                    if data["tkr_id"] == 3:
                        await self.server_queue.put({"action": "lvl1", "data": data})

                case "GetAccountPositions":
                    await self.data_queue.put({
                        "action": "acct",
                        "data": json.loads(response["o"])
                    })

                case "SendOrder":
                    # Order confirmation
                    await self.data_queue.put({
                        "action": "o",
                        "data": json.loads(response["o"])
                    })

                case "LogOut":
                    await self.db_queue.put({"action": "quit"})
                    print(response)
                    break

                case _:
                    print(response)

    async def start_sender(self):
        while True:
            message = await self.sender_queue.get()
            match message["action"]:
                case "quit":
                    if self.authenticated is True:
                        await self.logout()
                    print("Stopping ndax sender")
                    break

                case "order":
                    print("Sending: {}".format(message))
                    await self.send_order(
                        message["data"]["tkr"],
                        message["data"]["order_id"],
                        message["data"]["side"],
                        message["data"]["qty"]
                    )

                case "acct":
                    print("Getting account positions")
                    await self.get_account_pos()

    async def server_handler(self, ws):
        self.server_clients.add(ws)
        try:
            await ws.wait_closed()
        finally:
            self.server_clients.remove(ws)

    async def server(self):
        while True:
            message = await self.server_queue.get()
            message["data"] = {
                key: float(value)
                if isinstance(value, dec)
                else value
                for key, value in message["data"].items()
            }
            for ws in self.server_clients:
                try:
                    await ws.send(json.dumps(message))
                except Exception as e:
                    print(e)

    async def start_server(self):
        async with websockets.serve(self.server_handler, "localhost", self.server_port):
            await self.server()

    async def start(self):
        print("Starting NdaxWs client:", self.uri)
        async with websockets.connect(self.uri) as ws:
            self.ws = ws
            await self.authenticate()

            try:
                if self.authenticated:
                    # await self.subscribe_tkr()
                    await self.subscribe_lvl1()
                    await asyncio.gather(
                        self.start_receiver(),
                        self.start_sender(),
                        self.start_server()
                    )
            except Exception as e:
                print(e)
            except asyncio.CancelledError:
                print("Continuing websocket")
                await asyncio.gather(
                    self.start_receiver(),
                    self.start_sender()
                )
