//! Planner elapsed time without the unsupported std clock on wasm32-unknown-unknown.

#[cfg(not(target_arch = "wasm32"))]
pub struct PlannerClock(std::time::Instant);

#[cfg(not(target_arch = "wasm32"))]
impl PlannerClock {
    pub fn now() -> Result<Self, String> {
        Ok(Self(std::time::Instant::now()))
    }

    pub fn elapsed_seconds(&self) -> Result<f64, String> {
        Ok(self.0.elapsed().as_secs_f64())
    }
}

#[cfg(target_arch = "wasm32")]
pub struct PlannerClock(u64);

#[cfg(target_arch = "wasm32")]
#[link(wasm_import_module = "wasi_snapshot_preview1")]
extern "C" {
    fn clock_time_get(clock_id: u32, precision: u64, timestamp: *mut u64) -> u32;
}

#[cfg(target_arch = "wasm32")]
fn monotonic_nanos() -> Result<u64, String> {
    const CLOCK_MONOTONIC: u32 = 1;
    let mut timestamp = 0_u64;
    // WASI writes one u64 to the aligned, live local only when it returns success.
    let errno = unsafe { clock_time_get(CLOCK_MONOTONIC, 1, &mut timestamp) };
    if errno != 0 {
        return Err(format!(
            "WASI monotonic clock_time_get failed with errno {errno}"
        ));
    }
    Ok(timestamp)
}

#[cfg(target_arch = "wasm32")]
impl PlannerClock {
    pub fn now() -> Result<Self, String> {
        Ok(Self(monotonic_nanos()?))
    }

    pub fn elapsed_seconds(&self) -> Result<f64, String> {
        let elapsed = monotonic_nanos()?
            .checked_sub(self.0)
            .ok_or_else(|| "WASI monotonic clock moved backwards".to_string())?;
        Ok(elapsed as f64 / 1_000_000_000.0)
    }
}
