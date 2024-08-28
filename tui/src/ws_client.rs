// use tokio::net::TcpStream;
use tokio_tungstenite::{
    connect_async,
    // tungstenite::{Error, Result},
};
use tokio::sync::mpsc::Sender;
use futures_util::StreamExt;     // StreamExt, extends the trait to allow .next()
// use tokio_tungstenite::{MaybeTlsStream, WebSocketStream};
use tokio_tungstenite::tungstenite::protocol::Message;
use anyhow::Result;
use serde_json;


pub struct WsClient {
    url: String,
    tx: Sender<String>,
}


impl WsClient {
    pub fn new(url: String, tx: Sender<String>) -> Self {
        Self {
            url,
            tx,
        }
    }

    pub async fn run(&self) -> Result<()> {
        // println!("running: {}", self.url); // self is behind a reference, what happens to uri
        let (mut ws_stream, _response) = connect_async(&self.url).await.unwrap();      // Need to handle here, no returns
        
        while let Some(msg) = ws_stream.next().await {
            match msg {
                Ok(Message::Text(text)) => {
                    // println!("Received message: {}", text);
                    // let data = serde_json::from_str(&text)?;
                    self.tx.send(text).await.unwrap();
                },
                Err(e) => {
                    println!("Error message: {}", e);
                },
                _ => {},
            }
        }
        Ok(())
    }
}
