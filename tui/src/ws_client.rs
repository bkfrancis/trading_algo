use anyhow::{anyhow, Result};
use cli_log::*;
use futures_util::StreamExt; // StreamExt, extends the trait to allow .next()
use serde::{Deserialize, Serialize};
use serde_json;
use tokio::sync::mpsc::Sender;
use tokio_tungstenite::{connect_async, tungstenite::protocol::Message};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Lvl1Data {
    pub timestamp_ms: i64,
    pub tkr_id: i64,
    pub tkr: String,
    pub best_bid: f64,
    pub best_ask: f64,
    pub last_trade_price: f64,
    pub last_trade_qty: f64,
    pub last_trade_time: i64,
}

impl Default for Lvl1Data {
    fn default() -> Self {
        Self {
            timestamp_ms: 0,
            tkr_id: 0,
            tkr: String::from("-"),
            best_bid: 0.0,
            best_ask: 0.0,
            last_trade_price: 0.0,
            last_trade_qty: 0.0,
            last_trade_time: 0,
        }
    }
}

#[derive(Serialize, Deserialize, Debug)]
struct Lvl1Msg {
    action: String,
    data: Lvl1Data,
}

pub struct WsClient {
    url: String,
    tx: Sender<Option<Lvl1Data>>,
}

impl WsClient {
    pub fn new(url: String, tx: Sender<Option<Lvl1Data>>) -> Self {
        Self { url, tx }
    }

    pub async fn run(&mut self) -> Result<()> {
        info!("Starting websocket client: {}", self.url);
        let (mut ws_stream, _resp) = connect_async(&self.url).await?;
        info!("Connected to: {}", self.url);

        while let Some(msg) = ws_stream.next().await {
            debug!("received msg");
            match msg {
                Ok(Message::Text(text)) => {
                    info!("ws message: {}", text);
                    let parsed_msg: Lvl1Msg = serde_json::from_str(&text)?;
                    debug!("{:#?}", parsed_msg);
                    self.tx.send(Some(parsed_msg.data)).await?;
                }
                Err(e) => return Err(anyhow!(e)),
                _ => {}
            }
        }
        Ok(())
    }
}
