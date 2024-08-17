import asyncio
import mariadb


class MariaDbClient:
    def __init__(self, live, user, pswd, host, port, db, db_queue):
        self.live = live
        self.user = user
        self.pswd = pswd
        self.host = host
        self.port = port
        self.db = db
        self.db_queue = db_queue
        self.conn = None
        self.trade_history_table = self.get_trade_history_table()

    def get_trade_history_table(self):
        if not self.live:
            return "paper_trade_history"
        else:
            return "trade_history"

    async def clear_paper_orders(self):
        print("Clearing data from:", self.trade_history_table)
        cur = self.conn.cursor()
        cur.execute(
            """
            DELETE
            FROM paper_trade_history
            """
        )
        self.conn.commit()
        cur.close()

    async def save_order(self, order):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT {}(
                timestamp_ms,
                tkr_id,
                price,
                fee,
                action
            )
            VALUES
            (?, ?, ?, ?, ?)
            """.format(self.trade_history_table)
        )
        cur.close()

    async def save_tkr(self, data):
        cur = self.conn.cursor()
        cur.executemany(
            """
            INSERT IGNORE ndax_tkr_data(
                timestamp_ms,
                high,
                low,
                open,
                close,
                volume,
                inside_bid_price,
                inside_ask_price,
                tkr_id,
                timestamp_beg_ms
            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            data
        )
        self.conn.commit()
        cur.close()

    async def save_lvl1(self, data):
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT IGNORE ndax_lvl1_data(
                timestamp_ms,
                tkr_id,
                best_bid,
                best_ask,
                last_trade_price,
                last_trade_qty,
                last_trade_time
            )
            VALUES
            (?, ?, ?, ?, ?, ?, ?)
            """,
            list(data.values())
        )
        self.conn.commit()
        cur.close()

    async def start_receiver(self):
        print("starting mariadb receiver")
        while True:
            message = await self.db_queue.get()
            print("db data queue", message)

            match message["action"]:
                case "quit":
                    print("db client closing")
                    self.conn.close()
                    break

                case "tkr":
                    await self.save_tkr(message["data"])

                case "order":
                    await self.save_order(message["data"])

                case "lvl1":
                    await self.save_lvl1(message["data"])

    async def start(self):
        print("Starting MariaDB client")
        try:
            self.conn = mariadb.connect(
                user=self.user, password=self.pswd, host=self.host, port=self.port, database=self.db
            )

            await self.start_receiver()

        except Exception as e:
            print(e)
            self.conn.close()

        except asyncio.CancelledError:
            print("Cancelling db client")
            await self.start_receiver()
