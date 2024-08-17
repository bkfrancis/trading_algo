from dotenv import load_dotenv
import os
import asyncio
from trading_client import TradingClient
from mariadb_client import MariaDbClient
from ndax_client import NdaxConfig, NdaxClient


async def main():
    load_dotenv()
    LIVE = os.getenv("LIVE", "False") != "False"
    TRADING_FEE = os.getenv("TRADING_FEE", 0)

    data_queue = asyncio.Queue(maxsize=25)
    sender_queue = asyncio.Queue(maxsize=25)
    db_queue = asyncio.Queue(maxsize=25)

    fiat_id = int(os.getenv("FIAT_ID"))
    tkr_id = int(os.getenv("TKR_ID"))
    trading_client = TradingClient(
        LIVE, fiat_id, tkr_id, data_queue, sender_queue, TRADING_FEE
    )

    DB_USER = os.getenv("DB_USER")
    DB_PSWD = os.getenv("DB_PSWD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT"))
    DB_NAME = os.getenv("DB_NAME")
    db_client = MariaDbClient(LIVE, DB_USER, DB_PSWD, DB_HOST, DB_PORT, DB_NAME, db_queue)

    ndax_config = NdaxConfig()
    ndax_config.live = LIVE
    ndax_config.api_key = os.getenv("API_KEY")
    ndax_config.secret = os.getenv("SECRET")
    ndax_config.user_id = os.getenv("USER_ID")
    ndax_config.acct_id = os.getenv("ACCT_ID")
    ndax_config.uri = os.getenv("WS_URI")
    ndax_config.oms_id = os.getenv("OMS_ID")
    ndax_config.tkr_list = [tkr_id]
    ndax_config.ws_api_port = int(os.getenv("WS_API_PORT"))
    ws_client = NdaxClient(ndax_config, sender_queue, data_queue, db_queue)

    try:
        print("Starting app... LIVE Trading:", LIVE)
        await asyncio.gather(
            ws_client.start(),
            db_client.start(),
            trading_client.start(),
            return_exceptions=True
        )

    except Exception as e:
        print(e)

    except asyncio.CancelledError:
        print("Cancelling main")


asyncio.run(main())
