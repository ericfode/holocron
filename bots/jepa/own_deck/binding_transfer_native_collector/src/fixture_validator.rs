//! Separate executable: refusing ordinary collection is mandatory, not a default.
#[path = "main.rs"]
mod collector;

fn main() {
    collector::entry(true);
}
