from dotenv import load_dotenv
import os
import asyncio
from trading_client import TradingClient
from mariadb_client import MariaDbClient
from ndax_client import NdaxConfig, NdaxClient


async def main():
    load_dotenv()
    SIM = os.getenv("SIM", "True") != "False"
    TRADING_FEE = os.getenv("TRADING_FEE", 0)

    data_queue = asyncio.Queue(maxsize=25)
    sender_queue = asyncio.Queue(maxsize=25)
    db_queue = asyncio.Queue(maxsize=25)
    fiat_id = int(os.getenv("FIAT_ID"))
    tkr_id = int(os.getenv("TKR_ID"))
    trading_client = TradingClient(
        SIM, fiat_id, tkr_id, data_queue, sender_queue, db_queue, TRADING_FEE
    )

    DB_USER = os.getenv("DB_USER")
    DB_PSWD = os.getenv("DB_PSWD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT"))
    DB_NAME = os.getenv("DB_NAME")
    db_client = MariaDbClient(SIM, DB_USER, DB_PSWD, DB_HOST, DB_PORT, DB_NAME, db_queue)

    ndax_config = NdaxConfig()
    ndax_config.api_key = os.getenv("API_KEY")
    ndax_config.secret = os.getenv("SECRET")
    ndax_config.user_id = os.getenv("USER_ID")
    ndax_config.acct_id = os.getenv("ACCT_ID")
    ndax_config.uri = os.getenv("WS_URI")
    ndax_config.oms_id = os.getenv("OMS_ID")
    ndax_config.tkr_list = [tkr_id]
    ws_client = NdaxClient(ndax_config, sender_queue, data_queue)

    try:
        print("Starting trading... SIM mode:", SIM)
        await asyncio.gather(
            ws_client.start(),
            db_client.start(),
            trading_client.start(),
            return_exceptions=True
        )

    except Exception as e:
        print(e)

    except asyncio.CancelledError:
        print("Shutting down main")


asyncio.run(main())
