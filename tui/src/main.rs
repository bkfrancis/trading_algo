use anyhow::Result;
use cli_log::*;
use ratatui::{
    backend::CrosstermBackend,
    crossterm::{
        terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
        ExecutableCommand,
    },
    Terminal,
};
use std::io::stdout;
use tokio::sync::mpsc::{self, Receiver, Sender};

mod tui;
mod ws_client;
use tui::Tui;
use ws_client::{Lvl1Data, WsClient};

#[tokio::main]
async fn main() -> Result<()> {
    init_cli_log!();
    stdout().execute(EnterAlternateScreen)?;
    enable_raw_mode()?;

    let (tx, rx): (Sender<Option<Lvl1Data>>, Receiver<Option<Lvl1Data>>) = mpsc::channel(5);
    let url: String = "ws://localhost:8765".into();
    let mut ws = WsClient::new(url, tx);

    let mut terminal = Terminal::new(CrosstermBackend::new(stdout()))?;
    terminal.clear()?;
    let mut tui = Tui::new(terminal, rx);

    // Concurrent
    let result = tokio::try_join!(ws.run(), tui.run());
    match result {
        Ok((_ws, _tui)) => {}
        Err(e) => debug!("Tasks interrupted: {}", e),
    }

    stdout().execute(LeaveAlternateScreen)?;
    disable_raw_mode()?;

    Ok(())
}
