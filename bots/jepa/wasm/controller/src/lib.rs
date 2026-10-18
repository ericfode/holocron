//! The table JEPA's protocol and search policy. Numerical inference belongs to `Model` implementations.
mod clock;
pub mod controller;
pub mod features;
pub mod own_deck;
pub mod resource;
pub mod rng;

pub use controller::{Config, JepaBot, Model, ModelRole, PlanConfig, Simulator, Stats};
pub use features::{encode, CardTables, Encoded};
