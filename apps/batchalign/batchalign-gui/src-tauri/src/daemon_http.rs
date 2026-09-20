//! Bounded HTTP requests shared by the desktop's native IPC relay.
use std::time::Duration;

pub async fn request(
    port: u16,
    method: &str,
    path: &str,
    body: Option<serde_json::Value>,
    timeout: Duration,
) -> Result<serde_json::Value, String> {
    if !path.starts_with('/') || path.starts_with("//") {
        return Err("daemon request path must start with a single /".into());
    }
    let method = match method {
        "GET" => reqwest::Method::GET,
        "POST" => reqwest::Method::POST,
        "PUT" => reqwest::Method::PUT,
        "DELETE" => reqwest::Method::DELETE,
        other => return Err(format!("unsupported method {other}")),
    };
    let client = reqwest::Client::builder()
        .no_proxy()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(timeout)
        .build()
        .map_err(|error| error.to_string())?;
    let mut request = client.request(method.clone(), format!("http://127.0.0.1:{port}{path}"));
    if let Some(body) = body {
        request = request.json(&body);
    }
    let response = request
        .send()
        .await
        .map_err(|error| format!("{method} {path}: {error}"))?;
    let status = response.status();
    let bytes = response
        .bytes()
        .await
        .map_err(|error| format!("{method} {path}: {error}"))?;
    if !status.is_success() {
        return Err(format!(
            "{method} {path} → {status}: {}",
            String::from_utf8_lossy(&bytes)
        ));
    }
    if bytes.is_empty() {
        return Ok(serde_json::Value::Null);
    }
    serde_json::from_slice(&bytes).map_err(|error| format!("invalid JSON from daemon: {error}"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};
    use std::net::TcpListener;

    fn server(response: &'static str) -> (u16, std::thread::JoinHandle<()>) {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let worker = std::thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            stream
                .set_read_timeout(Some(Duration::from_secs(5)))
                .unwrap();
            let mut buffer = [0; 4096];
            stream.read(&mut buffer).unwrap();
            stream.write_all(response.as_bytes()).unwrap();
        });
        (port, worker)
    }

    #[test]
    fn relay_distinguishes_json_empty_error_and_malformed_responses() {
        let runtime = tokio::runtime::Runtime::new().unwrap();
        for (response, expected) in [
            (
                "HTTP/1.1 200 OK\r\nContent-Length: 11\r\n\r\n{\"ok\":true}",
                "json",
            ),
            ("HTTP/1.1 204 No Content\r\n\r\n", "empty"),
            (
                "HTTP/1.1 503 Unavailable\r\nContent-Length: 7\r\n\r\nmissing",
                "error",
            ),
            ("HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nbad", "invalid"),
        ] {
            let (port, worker) = server(response);
            let result = runtime.block_on(request(
                port,
                "GET",
                "/capabilities",
                None,
                Duration::from_secs(5),
            ));
            worker.join().unwrap();
            match expected {
                "json" => assert_eq!(result.unwrap(), serde_json::json!({"ok": true})),
                "empty" => assert_eq!(result.unwrap(), serde_json::Value::Null),
                "error" => assert!(
                    result
                        .unwrap_err()
                        .contains("503 Service Unavailable: missing")
                ),
                _ => assert!(result.unwrap_err().contains("invalid JSON")),
            }
        }
    }

    #[test]
    fn stalled_response_body_is_bounded() {
        // Headers arrive, but the promised body never does. A connect timeout
        // alone cannot prevent this from hanging status polling forever.
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let worker = std::thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            let mut buffer = [0; 4096];
            stream.read(&mut buffer).unwrap();
            stream
                .write_all(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n")
                .unwrap();
            std::thread::sleep(Duration::from_millis(300));
        });
        let result = tokio::runtime::Runtime::new().unwrap().block_on(request(
            port,
            "GET",
            "/jobs/test",
            None,
            Duration::from_millis(100),
        ));
        assert!(result.is_err());
        worker.join().unwrap();
    }
}
