//! New executable identity; the validated scientific/fixture source is unchanged.
#[path = "main.rs"]
mod collector;

fn main() {
    collector::entry(false);
}
