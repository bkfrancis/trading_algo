use anyhow::{anyhow, Result};
use chrono::{DateTime, Local};
use cli_log::*;
use ratatui::{
    backend::Backend,
    crossterm::event::{self, KeyCode, KeyEventKind},
    layout::{Constraint, Layout},
    style::{Color, Stylize},
    widgets::{Block, Cell, Paragraph, Row, Table},
    Frame, Terminal,
};
use tokio::sync::mpsc::Receiver;

use crate::ws_client::Lvl1Data;

pub struct Tui<B: Backend> {
    terminal: Terminal<B>,
    rx: Receiver<Option<Lvl1Data>>,
}

impl<B: Backend> Tui<B> {
    pub fn new(terminal: Terminal<B>, rx: Receiver<Option<Lvl1Data>>) -> Self {
        Self { terminal, rx }
    }

    pub async fn run(&mut self) -> Result<()> {
        info!("Starting UI");
        let mut data_list = DataList::new(100);

        loop {
            // Initial draw of ui
            self.terminal.draw(|f| ui(f, &data_list))?;

            // Handle key press q to quit
            // Sets 16ms delay
            match self.handle_event() {
                Ok(true) => {}
                Ok(false) => {
                    info!("User interrupt");
                    return Err(anyhow!("User interrupt"));
                }
                Err(e) => return Err(anyhow!(e)),
            }
            match self.rx.try_recv() {
                Ok(data) => {
                    // Draw on new data
                    data_list.insert(data.unwrap());
                    info!("drawing frame");
                    self.terminal.draw(|f| ui(f, &data_list))?;
                }
                Err(_e) => {}
            }

            tokio::task::yield_now().await;
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

fn ui(frame: &mut Frame, data_list: &DataList) {
    let [header_area, main_area, footer_area] = Layout::vertical([
        Constraint::Length(1),
        Constraint::Min(0),
        Constraint::Length(1),
    ])
    .areas(frame.area());
    let [left_area, right_area] =
        Layout::horizontal([Constraint::Percentage(50), Constraint::Percentage(50)])
            .areas(main_area);
    frame.render_widget(Paragraph::new("Trading Dashboard"), header_area);
    frame.render_widget(Paragraph::new("Press q to quit..."), footer_area);

    // Summary
    let curr_i = data_list.curr_i;
    let summary_arr = [
        Row::new(["TKR:".to_string(), data_list.data[curr_i].tkr.clone()]),
        Row::new([
            "Price:".to_string(),
            format!("{:.2}", data_list.data[curr_i].last_trade_price),
        ]),
        Row::new([
            "Quantity:".to_string(),
            data_list.data[curr_i].last_trade_qty.to_string(),
        ]),
        Row::new([
            "Last Trade:".to_string(),
            DateTime::from_timestamp_millis(data_list.data[curr_i].last_trade_time)
                .unwrap()
                .with_timezone(&Local)
                .to_string(),
        ]),
    ];
    frame.render_widget(
        Table::new(
            summary_arr,
            [Constraint::Length(12), Constraint::Length(30)],
        )
        .block(Block::bordered().title("Summary")),
        left_area,
    );

    // Level 1 Quotes
    let headers = Row::new(["TKR", "Price", "Quantity", "Time", "Bid", "Ask"])
        .bg(Color::Rgb(205, 214, 244))
        .fg(Color::Rgb(17, 17, 27));
    frame.render_widget(
        Table::new(
            data_list.get_rows(),
            [
                Constraint::Length(12),
                Constraint::Length(12),
                Constraint::Length(12),
                Constraint::Length(12),
                Constraint::Length(12),
                Constraint::Length(12),
            ],
        )
        .header(headers)
        .block(Block::bordered().title("Level 1 Quotes")),
        right_area,
    );
}

// Level 1 Quotes
struct DataList {
    capacity: usize,
    insert_i: usize,
    curr_i: usize,
    data: Vec<Lvl1Data>,
}

impl DataList {
    fn new(n: usize) -> Self {
        Self {
            capacity: n,
            insert_i: 0,
            curr_i: 99,
            data: vec![Lvl1Data::default(); n],
        }
    }

    fn insert(&mut self, data: Lvl1Data) {
        self.data[self.insert_i] = data;
        self.insert_i = (self.insert_i + 1) % self.capacity;

        self.curr_i = (self.capacity - 1) - ((self.capacity - self.insert_i) % self.capacity)
    }

    fn get_rows(&self) -> Vec<Row> {
        // Order data
        let mut i = self.curr_i;
        let mut data_vec: Vec<Row> = Vec::with_capacity(self.capacity - 1);
        for _ in 0..(self.capacity - 1) {
            let i_prior = (self.capacity - 1) - ((self.capacity - i) % self.capacity);

            // Bid cell color
            let mut bid_fg_color: Color;
            if self.data[i].best_bid > self.data[i_prior].best_bid {
                bid_fg_color = Color::Rgb(166, 227, 161);
            } else if self.data[i].best_bid < self.data[i_prior].best_bid {
                bid_fg_color = Color::Rgb(243, 139, 168);
            } else {
                bid_fg_color = Color::Reset;
            }

            // Ask cell color
            let mut ask_fg_color: Color;
            if self.data[i].best_ask > self.data[i_prior].best_ask {
                ask_fg_color = Color::Rgb(166, 227, 161);
            } else if self.data[i].best_ask < self.data[i_prior].best_ask {
                ask_fg_color = Color::Rgb(243, 139, 168);
            } else {
                ask_fg_color = Color::Reset;
            }

            // Check price change for row color
            let bg_color: Color;
            let fg_color: Color;
            if self.data[i].last_trade_price > self.data[i_prior].last_trade_price {
                bg_color = Color::Rgb(166, 227, 161);
                fg_color = Color::Rgb(24, 24, 27);
                bid_fg_color = fg_color;
                ask_fg_color = fg_color;
            } else if self.data[i].last_trade_price < self.data[i_prior].last_trade_price {
                bg_color = Color::Rgb(243, 139, 168);
                fg_color = Color::Rgb(24, 24, 27);
                bid_fg_color = fg_color;
                ask_fg_color = fg_color;
            } else {
                bg_color = Color::Reset;
                fg_color = Color::Reset;
            }

            // Create rows
            data_vec.push(
                Row::new([
                    Cell::new(self.data[i].tkr.clone()),
                    Cell::new(format!("{:.2}", self.data[i].last_trade_price)),
                    Cell::new(format!("{:.4}", self.data[i].last_trade_qty)),
                    Cell::new(
                        DateTime::from_timestamp_millis(self.data[i].timestamp_ms)
                            .unwrap()
                            .with_timezone(&Local)
                            .format("%H:%M:%S")
                            .to_string(),
                    ),
                    Cell::new(format!("{:.2}", self.data[i].best_bid)).fg(bid_fg_color),
                    Cell::new(format!("{:.2}", self.data[i].best_ask)).fg(ask_fg_color),
                ])
                .bg(bg_color)
                .fg(fg_color),
            );
            i = i_prior;
        }
        data_vec
    }
}
