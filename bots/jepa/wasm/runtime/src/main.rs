#![cfg_attr(target_arch = "wasm32", no_main)]
mod backend;
mod transport;
use backend::KernelModel;
use jepa_controller::{Config, JepaBot};
use serde_json::Value;

fn serve() -> Result<(), String> {
    let config: Config = match transport::config()? {
        Some(text) => serde_json::from_str(&text).map_err(|e| format!("configuration: {e}"))?,
        None => Config::default(),
    };
    let mut bot = JepaBot::new(config);
    let mut model = KernelModel::new()?;
    let mut wire = transport::Wire::new();
    while let Some(msg) = wire.read()? {
        let reply = match msg.get("t").and_then(Value::as_str) {
            Some("hello") => {
                if !msg["versions"]
                    .as_array()
                    .is_some_and(|versions| versions.iter().any(|v| v.as_u64() == Some(2)))
                {
                    return Err("this bundle requires protocol v2".into());
                }
                let ready = bot.hello(&msg);
                if ready["v"].as_u64() != Some(2) || ready["sim"].as_bool() != Some(true) {
                    return Err("this bundle requires the v2 simulator planner".into());
                }
                ready
            }
            Some("decide") => bot.decide(&msg, &mut model, &mut |request| {
                wire.write(&request)?;
                let reply = wire.read()?.ok_or("EOF awaiting simulated reply")?;
                if reply.get("t").and_then(Value::as_str) != Some("simulated") {
                    return Err("expected simulated reply".into());
                }
                Ok(reply)
            })?,
            Some("over") => bot.over(),
            #[cfg(feature = "diagnostics")]
            Some("tensor") => tensor(&mut model, &msg)?,
            #[cfg(feature = "diagnostics")]
            Some("stats") => serde_json::json!({"t":"stats","controller":bot.stats,
                "contextCalls":model.stats.context_calls,"predictCalls":model.stats.predict_calls,
                "cacheHits":model.stats.context_cache_hits}),
            _ => return Err("unknown protocol message".into()),
        };
        wire.write(&reply)?;
    }
    Ok(())
}

#[cfg(feature = "diagnostics")]
fn tensor(model: &mut KernelModel, msg: &Value) -> Result<Value, String> {
    use jepa_controller::{Encoded, Model, ModelRole};
    let e: Encoded = serde_json::from_value(msg["encoded"].clone()).map_err(|e| e.to_string())?;
    let role = match msg["role"].as_str() {
        Some("raw") => ModelRole::Raw,
        Some("evaluator") => ModelRole::Evaluator,
        _ => return Err("invalid diagnostic role".into()),
    };
    let horizon = msg["horizon"].as_str().ok_or("missing horizon")?;
    let value = model.context_value(role, &e)?;
    let logits = model.predict_values(role, &e, horizon)?;
    Ok(
        serde_json::json!({"t":"tensor","value":value,"logits":logits,
        "kernelStats":{"contextCalls":model.stats.context_calls,"predictCalls":model.stats.predict_calls,
        "cacheHits":model.stats.context_cache_hits}}),
    )
}

#[cfg(not(target_arch = "wasm32"))]
fn main() {
    if let Err(e) = serve() {
        eprintln!("jepa: {e}");
        std::process::exit(1);
    }
}
#[cfg(target_arch = "wasm32")]
#[no_mangle]
pub extern "C" fn _start() {
    match serve() {
        Ok(()) => transport::exit(0),
        Err(e) => {
            let _ = transport::write_bytes(2, format!("jepa: {e}\n").as_bytes());
            transport::exit(1);
        }
    }
}
