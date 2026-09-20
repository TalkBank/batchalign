//! Daemon → frontend progress relay.
//!
//! For each active batch we open one SSE stream to
//! `GET /jobs/{job_id}/events`, parse the `progress` events (the daemon
//! writes them as `event: progress\ndata: <json>`), wrap each in
//! `ProgressV2Payload`, and emit on the `progress-v2` Tauri channel.
//!
//! Replacement and daemon shutdown cancel both pending connections and active
//! streams. Identity-checked cleanup cannot remove a newer pump for the batch.

use std::pin::Pin;

use eventsource_stream::Eventsource;
use futures_util::stream::StreamExt;
use tauri::{AppHandle, Emitter, Manager};

use crate::protocol::{ProgressV2Payload, events};
use crate::state::AppState;

pub async fn pump(app: AppHandle, batch_id: String, job_id: String) {
    let state = app.state::<AppState>();
    let Some(daemon) = state.daemon.load_full() else {
        return;
    };
    let mut shutdown = daemon.shutdown.subscribe();
    let (identity, cancel) = state.register_pump(batch_id.clone()).await;
    if !*shutdown.borrow() {
        tokio::select! {
            biased;
            _ = cancel => {},
            _ = shutdown.changed() => {},
            _ = relay(&app, &batch_id, &job_id, daemon.port) => {},
        }
    }
    state.finish_pump(&batch_id, &identity).await;
}

async fn relay(app: &AppHandle, batch_id: &str, job_id: &str, port: u16) {
    let url = format!(
        "http://127.0.0.1:{port}/jobs/{job_id}/events",
        port = port,
        job_id = job_id,
    );
    let client = match reqwest::Client::builder()
        .no_proxy()
        .redirect(reqwest::redirect::Policy::none())
        .connect_timeout(std::time::Duration::from_secs(5))
        .build()
    {
        Ok(client) => client,
        Err(error) => {
            eprintln!("[daemon events] SSE client failed for {job_id}: {error}");
            return;
        }
    };
    // Bound response headers separately: the event body itself may legitimately
    // stay open for hours while a pipeline runs.
    let response =
        match tokio::time::timeout(std::time::Duration::from_secs(30), client.get(&url).send())
            .await
        {
            Ok(response) => response,
            Err(error) => {
                eprintln!("[daemon events] SSE headers timed out for {job_id}: {error}");
                return;
            }
        };
    let resp = match response {
        Ok(r) => match r.error_for_status() {
            Ok(response) => response,
            Err(error) => {
                eprintln!("[daemon events] SSE request failed for {job_id}: {error}");
                return;
            }
        },
        Err(e) => {
            eprintln!("[daemon events] SSE connect failed for {job_id}: {e}");
            return;
        }
    };

    let mut stream: Pin<Box<_>> = Box::pin(resp.bytes_stream().eventsource());

    while let Some(event) = stream.next().await {
        let event = match event {
            Ok(event) => event,
            Err(error) => {
                eprintln!("[daemon events] SSE stream failed for {job_id}: {error}");
                break;
            }
        };
        if event.event == "done" {
            break;
        }
        if event.event != "progress" {
            continue;
        }
        let parsed: serde_json::Value = match serde_json::from_str(&event.data) {
            Ok(value) => value,
            Err(_) => continue,
        };
        let _ = app.emit(
            events::PROGRESS_V2,
            ProgressV2Payload {
                batch_id: batch_id.to_owned(),
                job_id: job_id.to_owned(),
                event: parsed,
            },
        );
    }
}
