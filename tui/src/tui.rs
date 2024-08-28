use ratatui::{
    crossterm::event::{self, KeyCode, KeyEventKind},
    layout::{Constraint, Layout},
    // style::{Color, Stylize},
    widgets::{Block, Paragraph},
    Frame,
    Terminal,
    backend::Backend,
};
use tokio::sync::mpsc::Receiver;
use anyhow::{anyhow, Result};

// Tui genereic over trait B
#[allow(dead_code)]
pub struct Tui<B: Backend> {
    terminal: Terminal<B>,
    rx: Receiver<String>,
}

impl<B: Backend> Tui<B> {
    pub fn new(terminal: Terminal<B>, rx: Receiver<String>) -> Self {
        Self {
            terminal,
            rx,
        }
    }

    pub async fn run(&mut self) -> Result<()> {
        loop {
            // Handle key press q to quit
            // Sets 16ms delay
            match self.handle_event() {
                Ok(true) => {},
                Ok(false) => {
                    return Err(anyhow!("User interrupt"))
                },
                Err(e) => {
                    return Err(anyhow!(e))
                },
            }
            // Receive websocket data from channel
            match self.rx.try_recv() {
                Ok(data) => {
                    println!("data: {}", data);
                },
                _ => {},
            }
            self.terminal.draw(ui)?;
        }
    }

    fn handle_event(&self) -> Result<bool> {
        if event::poll(std::time::Duration::from_millis(16))? {
            if let event::Event::Key(key) = event::read()? {
                if key.kind == KeyEventKind::Press && key.code == KeyCode::Char('q') {
                    return Ok(false);
                }
            }
        }
        Ok(true)
    }
}


fn ui(frame: &mut Frame) {
    let [header_area, main_area, footer_area] = Layout::vertical([
        Constraint::Length(1), // Height in columns
        Constraint::Min(0),
        Constraint::Length(1),
    ])
    .areas(frame.area());
    let [left_area, right_area] =
        Layout::horizontal([Constraint::Percentage(50), Constraint::Percentage(50)])
            .areas(main_area);

    frame.render_widget(Paragraph::new("Trading Dashboard"), header_area);
    frame.render_widget(Paragraph::new("Press q to quit..."), footer_area);

    frame.render_widget(
        Paragraph::new("new bordered paragraph.")
            // .fg(Color::Rgb(205, 214, 244))
            .block(Block::bordered().title("Summary")),
        left_area,
    );
    frame.render_widget(
        Paragraph::new("left area").block(Block::bordered().title("Level 1 Quotes")),
        right_area,
    );
}
