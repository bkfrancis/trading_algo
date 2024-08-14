import json
import random
import time
import asyncio
import hmac
import hashlib
import websockets
from decimal import Decimal as dec


class NdaxConfig:
    api_key = None
    secret = None
    user_id = None
    acct_id = None
    oms_id = None
    tkr_list = None


def tkr_parser(data_list):
    data_list = [
        (
            int(col[0]),    # date_time
            dec(col[1]),    # high
            dec(col[2]),    # low
            dec(col[3]),    # open
            dec(col[4]),    # close
            int(col[5]),    # volumne
            dec(col[6]),    # inside_bid_price
            dec(col[7]),    # inside_ask_price
            int(col[8]),    # tkr_id
            int(col[9])     # date_time_beg
        )
        for col in data_list
    ]
    return data_list


class NdaxClient:
    def __init__(self, config, sender_queue, data_queue):
        self.api_key = config.api_key
        self.secret = config.secret
        self.user_id = config.user_id
        self.acct_id = config.acct_id
        self.uri = config.uri
        self.oms_id = config.oms_id
        self.tkr_list = config.tkr_list
        self.sender_queue = sender_queue
        self.data_queue = data_queue
        self.ws = None
        self.authenticated = False

    def status(self):
        print(self.ws.open)

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
            "i": str(int(time.time())),
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
            await self.data_queue.put({"action": "q"})

    async def get_account_pos(self):
        payload = {
            "AccountId": self.acct_id,
            "OMSId": self.oms_id
        }
        message = {
            "m": 0,
            "i": str(int(time.time())),
            "n": "GetAccountPositions",
            "o": json.dumps(payload)
        }
        await self.ws.send(json.dumps(message))

    async def subscribe_tkr(self):
        for tkr in self.tkr_list:
            print("subscribing tkr:", tkr)
            payload = {
                "OMSId": self.oms_id,
                "InstrumentId": tkr,
                "Interval": 60,
                "IncludeLastCount": 0
            }
            message = {
                "m": 0,
                "i": str(int(time.time())),
                "n": "SubscribeTicker",
                "o": json.dumps(payload),
            }
            await self.ws.send(json.dumps(message))

    async def unsubscribe_tkr(self):
        for tkr in self.tkr_list:
            print("unsubscribing tkr:", tkr)
            payload = {
                "OMSId": self.oms_id,
                "InstrumentId": tkr,
            }
            message = {
                "m": 0,
                "i": str(int(time.time())),
                "n": "UnsubscribeTicker",
                "o": json.dumps(payload),
            }
            await self.ws.send(json.dumps(message))

    async def send_order(self, tkr_id, order_id, side, qty):
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
            "i": str(int(time.time())),
            "n": "SendOrder",
            "o": json.dumps(payload)
        }
        await self.ws.send(json.dumps(message))

    async def start_receiver(self):
        while True:
            response = await self.ws.recv()
            response = json.loads(response)

            match response["n"]:
                case "SubscribeTicker":
                    await self.data_queue.put(
                        {
                            "action": "t",
                            "data": tkr_parser(json.loads(response["o"]))
                        }
                    )

                case "UnsubscribeTicker":
                    print("Shutting down ndax receiver")
                    break

                case "TickerDataUpdateEvent":
                    await self.data_queue.put(
                        {
                            "action": "t",
                            "data": tkr_parser(json.loads(response["o"]))
                        }
                    )

                case "GetAccountPositions":
                    await self.data_queue.put(
                        {
                            "action": "a",
                            "data": json.loads(response["o"])
                        }
                    )

                case "SendOrder":
                    # Order confirmation
                    await self.data_queue.put(
                        {
                            "action": "o",
                            "data": json.loads(response["o"])
                        }
                    )

    async def start_sender(self):
        while True:
            message = await self.sender_queue.get()
            match message["action"]:
                case "q":
                    if self.authenticated is True:
                        await self.unsubscribe_tkr()
                    print("Shutting down ndax sender")
                    break

                case "o":
                    print("Sending: {}".format(message))
                    await self.send_order(
                        message["data"]["tkr"],
                        message["data"]["order_id"],
                        message["data"]["side"],
                        message["data"]["qty"]
                    )

                case "a":
                    print("Getting account positions")
                    await self.get_account_pos()

    async def start(self):
        print("Starting NdaxWs client:", self.uri)
        async with websockets.connect(self.uri) as ws:
            self.status
            self.ws = ws
            await self.authenticate()

            try:
                if self.authenticated:
                    await self.subscribe_tkr()

                    await asyncio.gather(
                        self.start_receiver(),
                        self.start_sender()
                    )

            except Exception as e:
                print(e)

            except asyncio.CancelledError:
                print("Continuing websocket")
                await asyncio.gather(
                    self.start_receiver(),
                    self.start_sender()
                )
