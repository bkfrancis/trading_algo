import asyncio


class TradingClient:
    def __init__(self, live, fiat_id, tkr_id, data_queue, sender_queue, trading_fee):
        self.live = live
        self.fiat_id = fiat_id
        self.tkr_id = tkr_id
        self.fiat_amount = 0
        self.crypto_amount = 0
        self.trading_fee = trading_fee
        self.price_data = []
        self.data_queue = data_queue
        self.sender_queue = sender_queue

    async def get_account_pos(self):
        # request to get account data
        if not self.live:
            self.fiat_amount = 10000
            self.crypto_amount = 0
        else:
            await self.sender_queue.put({"action": "a"})

    async def start_processing(self):
        while True:
            message = await self.data_queue.get()
            match message["action"]:
                case "quit":
                    raise asyncio.CancelledError

                case "acct":
                    # receive account information
                    for pos in message["data"]:
                        match pos["ProductId"]:
                            case self.fiat_id:
                                self.fiat_amount = pos["Amount"]
                                print("Fiat amount:", self.fiat_amount)
                            case self.tkr_id:
                                self.crypto_amount = pos["Amount"]
                                print("BTC amount:", self.crypto_amount)
                            case _:
                                pass

                case "tkr":
                    print("process tkr data")

    async def start(self):
        try:
            await asyncio.sleep(1)
            await self.get_account_pos()
            await self.start_processing()
        except asyncio.CancelledError:
            print("Initiating shut down sequence")
            await self.sender_queue.put({"action": "quit"})
