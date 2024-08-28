use std::io::{stdout, Result};
use ratatui::{
    backend::CrosstermBackend,
    crossterm::{
        terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
        ExecutableCommand,
    },
    Terminal,
};
use tokio::sync::mpsc;

mod ws_client;
mod tui;
use ws_client::WsClient;
use tui::Tui;


#[tokio::main]
async fn main() -> Result<()> {
    let (tx, rx) = mpsc::channel(5);

    let ws = WsClient::new("ws://localhost:8765".into(), tx);

    stdout().execute(EnterAlternateScreen)?;
    enable_raw_mode()?;
    let mut terminal = Terminal::new(CrosstermBackend::new(stdout()))?;
    terminal.clear()?;

    let mut tui = Tui::new(terminal , rx);
    
    let res = tokio::try_join!(ws.run(), tui.run());

    stdout().execute(LeaveAlternateScreen)?;
    disable_raw_mode()?;

    match res {
        Ok((_ws_res, _tui_res)) => {
            println!("Closing Program");
        },
        Err(err) => {
            println!("Tasks Interrupted: {}", err);
        },
    }

    Ok(())
}
