//! Small, dependency-free pieces of the native daemon startup contract.

/// Only explicit daemon announcements or uvicorn's loopback startup log are
/// readiness signals. Package-index URLs in bootstrap logs are not servers.
pub fn parse_port(line: &str) -> Option<u16> {
    let port = if let Some(rest) = line.strip_prefix("DAEMON_PORT=") {
        rest.trim().parse().ok()?
    } else {
        let (_, address) = line.split_once("Uvicorn running on ")?;
        let address = address
            .strip_prefix("http://")
            .or_else(|| address.strip_prefix("https://"))?;
        let rest = ["127.0.0.1:", "localhost:", "[::1]:"]
            .iter()
            .find_map(|host| address.strip_prefix(host))?;
        let end = rest
            .find(|c: char| !c.is_ascii_digit())
            .unwrap_or(rest.len());
        if end == 0 || rest[end..].starts_with(|c: char| !c.is_whitespace() && c != '/') {
            return None;
        }
        rest[..end].parse().ok()?
    };
    (port != 0).then_some(port)
}

pub fn push_tail(tail: &mut Vec<String>, text: &str) {
    let trimmed = text.trim_end();
    if trimmed.is_empty() {
        return;
    }
    // Bound both line count and line size, including Unicode output.
    tail.push(trimmed.chars().take(1024).collect());
    if tail.len() > 40 {
        tail.remove(0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_tcp_port_round_trips() {
        for port in 1..=u16::MAX {
            assert_eq!(parse_port(&format!("DAEMON_PORT={port}")), Some(port));
            assert_eq!(
                parse_port(&format!(
                    "INFO: Uvicorn running on http://127.0.0.1:{port} (Press CTRL+C to quit)"
                )),
                Some(port)
            );
        }
    }

    #[test]
    fn bootstrap_urls_never_announce_readiness() {
        for port in [1, 80, 443, 8000, 65535] {
            for host in ["127.0.0.1", "localhost", "pypi.org"] {
                assert_eq!(
                    parse_port(&format!("Downloading https://{host}:{port}/wheel.whl")),
                    None
                );
            }
        }
        for line in [
            "DAEMON_PORT=0",
            "DAEMON_PORT=65536",
            "DAEMON_PORT=-1",
            "DAEMON_PORT=12x",
            "Uvicorn running on http://example.com:8000",
            "Uvicorn running on http://localhost:0",
            "Uvicorn running on http://localhost:8000oops",
            "",
            "Application startup complete.",
        ] {
            assert_eq!(parse_port(line), None, "{line}");
        }
    }

    #[test]
    fn accepts_loopback_variants() {
        assert_eq!(parse_port("DAEMON_PORT= 1234 "), Some(1234));
        assert_eq!(
            parse_port("Uvicorn running on https://localhost:1234/"),
            Some(1234)
        );
        assert_eq!(
            parse_port("INFO: Uvicorn running on http://[::1]:1234"),
            Some(1234)
        );
    }

    #[test]
    fn diagnostic_tail_stays_bounded_under_large_unicode_logs() {
        let mut tail = Vec::new();
        let line = "é🚀".repeat(5000);
        for _ in 0..1000 {
            push_tail(&mut tail, &line);
        }
        assert_eq!(tail.len(), 40);
        assert!(tail.iter().all(|line| line.chars().count() <= 1024));
        push_tail(&mut tail, "   ");
        assert_eq!(tail.len(), 40);
        push_tail(&mut tail, "last error\n");
        assert_eq!(tail.last().unwrap(), "last error");
    }
}
