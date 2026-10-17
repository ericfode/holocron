//! Blocking newline JSON with one outstanding simulator request.
use serde_json::Value;
const MAX_LINE: usize = 8 * 1024 * 1024;
pub struct Wire {
    pending: Vec<u8>,
}
impl Wire {
    pub fn new() -> Self {
        Self {
            pending: Vec::new(),
        }
    }
    pub fn read(&mut self) -> Result<Option<Value>, String> {
        loop {
            if let Some(end) = self.pending.iter().position(|b| *b == b'\n') {
                let line: Vec<u8> = self.pending.drain(..=end).collect();
                if line.iter().all(u8::is_ascii_whitespace) {
                    continue;
                }
                return serde_json::from_slice(&line)
                    .map(Some)
                    .map_err(|e| format!("JSON input: {e}"));
            }
            if self.pending.len() >= MAX_LINE {
                return Err("input line too large".into());
            }
            let mut chunk = [0u8; 65536];
            let n = read_bytes(&mut chunk)?;
            if n == 0 {
                if self.pending.is_empty() {
                    return Ok(None);
                }
                return Err("input ended without newline".into());
            }
            self.pending.extend_from_slice(&chunk[..n]);
        }
    }
    pub fn write(&mut self, value: &Value) -> Result<(), String> {
        let mut line = serde_json::to_vec(value).map_err(|e| e.to_string())?;
        line.push(b'\n');
        write_bytes(1, &line)
    }
}
#[cfg(not(target_arch = "wasm32"))]
fn read_bytes(bytes: &mut [u8]) -> Result<usize, String> {
    use std::io::Read;
    std::io::stdin().read(bytes).map_err(|e| e.to_string())
}
#[cfg(not(target_arch = "wasm32"))]
pub fn write_bytes(fd: u32, bytes: &[u8]) -> Result<(), String> {
    use std::io::Write;
    if fd == 2 {
        std::io::stderr()
            .write_all(bytes)
            .map_err(|e| e.to_string())
    } else {
        let mut out = std::io::stdout();
        out.write_all(bytes)
            .and_then(|_| out.flush())
            .map_err(|e| e.to_string())
    }
}
#[cfg(not(target_arch = "wasm32"))]
pub fn config() -> Result<Option<String>, String> {
    if let Some(path) = std::env::args()
        .skip(1)
        .collect::<Vec<_>>()
        .windows(2)
        .find(|x| x[0] == "--config-file")
        .map(|x| x[1].clone())
    {
        return std::fs::read_to_string(path)
            .map(Some)
            .map_err(|e| e.to_string());
    }
    Ok(std::env::var("JEPA_CONFIG").ok())
}
#[cfg(target_arch = "wasm32")]
#[repr(C)]
struct IoVec {
    data: *mut u8,
    len: usize,
}
#[cfg(target_arch = "wasm32")]
#[link(wasm_import_module = "wasi_snapshot_preview1")]
extern "C" {
    fn fd_read(fd: u32, vectors: *const IoVec, count: usize, n: *mut usize) -> u16;
    fn fd_write(fd: u32, vectors: *const IoVec, count: usize, n: *mut usize) -> u16;
    fn environ_sizes_get(count: *mut usize, bytes: *mut usize) -> u16;
    fn environ_get(ptrs: *mut *mut u8, bytes: *mut u8) -> u16;
    fn proc_exit(status: u32) -> !;
}
#[cfg(target_arch = "wasm32")]
fn read_bytes(bytes: &mut [u8]) -> Result<usize, String> {
    let v = IoVec {
        data: bytes.as_mut_ptr(),
        len: bytes.len(),
    };
    let mut n = 0;
    let err = unsafe { fd_read(0, &v, 1, &mut n) };
    if err != 0 || n > bytes.len() {
        Err(format!("WASI fd_read: {err}"))
    } else {
        Ok(n)
    }
}
#[cfg(target_arch = "wasm32")]
pub fn write_bytes(fd: u32, mut bytes: &[u8]) -> Result<(), String> {
    while !bytes.is_empty() {
        let v = IoVec {
            data: bytes.as_ptr() as *mut u8,
            len: bytes.len(),
        };
        let mut n = 0;
        let err = unsafe { fd_write(fd, &v, 1, &mut n) };
        if err != 0 || n == 0 || n > bytes.len() {
            return Err(format!("WASI fd_write: {err}"));
        }
        bytes = &bytes[n..];
    }
    Ok(())
}
#[cfg(target_arch = "wasm32")]
pub fn config() -> Result<Option<String>, String> {
    let (mut count, mut len) = (0, 0);
    let err = unsafe { environ_sizes_get(&mut count, &mut len) };
    if err != 0 || count > 4096 || len > 1024 * 1024 {
        return Err(format!("WASI environment size: {err}"));
    }
    let mut ptrs = vec![std::ptr::null_mut(); count];
    let mut bytes = vec![0; len];
    let err = unsafe { environ_get(ptrs.as_mut_ptr(), bytes.as_mut_ptr()) };
    if err != 0 {
        return Err(format!("WASI environ_get: {err}"));
    }
    for item in bytes.split(|x| *x == 0) {
        if let Some(value) = item.strip_prefix(b"JEPA_CONFIG=") {
            return String::from_utf8(value.to_vec())
                .map(Some)
                .map_err(|e| e.to_string());
        }
    }
    Ok(None)
}
#[cfg(target_arch = "wasm32")]
pub fn exit(status: u32) -> ! {
    unsafe { proc_exit(status) }
}
