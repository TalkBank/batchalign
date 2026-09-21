// Included in the pinned PyApp process module by pyapp_install.sh.
// PyApp's read_to_string still captures diagnostics and validates UTF-8;
// this reader also forwards each chunk immediately to the desktop shell.
struct BootstrapProgressReader<R, W> {
    reader: R,
    writer: W,
}

impl<R, W> BootstrapProgressReader<R, W> {
    fn new(reader: R, writer: W) -> Self {
        Self { reader, writer }
    }
}

impl<R: std::io::Read, W: std::io::Write> std::io::Read for BootstrapProgressReader<R, W> {
    fn read(&mut self, buffer: &mut [u8]) -> std::io::Result<usize> {
        let count = self.reader.read(buffer)?;
        // Logging failure must not discard the installer's diagnostic output.
        let _ = self.writer.write_all(&buffer[..count]);
        let _ = self.writer.flush();
        Ok(count)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{self, Read, Write};
    use std::sync::mpsc;
    use std::time::Duration;

    #[test]
    fn output_is_visible_before_the_installer_exits() {
        struct Installer {
            emitted: bool,
            finish: mpsc::Receiver<()>,
        }
        impl Read for Installer {
            fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
                if self.emitted {
                    self.finish.recv_timeout(Duration::from_secs(3)).unwrap();
                    return Ok(0);
                }
                self.emitted = true;
                let line = b"Installing dependencies\n";
                buffer[..line.len()].copy_from_slice(line);
                Ok(line.len())
            }
        }
        struct Progress(mpsc::Sender<Vec<u8>>);
        impl Write for Progress {
            fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
                self.0.send(bytes.to_vec()).unwrap();
                Ok(bytes.len())
            }
            fn flush(&mut self) -> io::Result<()> { Ok(()) }
        }
        let (finish, finished) = mpsc::channel();
        let (progress, visible) = mpsc::channel();
        let worker = std::thread::spawn(move || {
            let mut reader = BootstrapProgressReader::new(
                Installer { emitted: false, finish: finished }, Progress(progress));
            let mut captured = String::new();
            reader.read_to_string(&mut captured).unwrap();
            captured
        });
        assert_eq!(visible.recv_timeout(Duration::from_secs(2)).unwrap(),
                   b"Installing dependencies\n");
        finish.send(()).unwrap();
        assert_eq!(worker.join().unwrap(), "Installing dependencies\n");
    }

    #[test]
    fn split_unicode_and_missing_final_newline_are_preserved() {
        struct Bytes(std::vec::IntoIter<u8>);
        impl Read for Bytes {
            fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
                if buffer.is_empty() { return Ok(0); }
                match self.0.next() {
                    Some(byte) => { buffer[0] = byte; Ok(1) }
                    None => Ok(0),
                }
            }
        }
        let expected = "Installing é_日本語\nfinished";
        let mut forwarded = Vec::new();
        let mut reader = BootstrapProgressReader::new(
            Bytes(expected.as_bytes().to_vec().into_iter()), &mut forwarded);
        let mut captured = String::new();
        reader.read_to_string(&mut captured).unwrap();
        assert_eq!(captured, expected);
        assert_eq!(forwarded, expected.as_bytes());
    }
}
