//! Pure feature-contract fixture encoder. Reads synthetic {cases:[{hello,variant}]} JSON.
use jepa_controller::own_deck::{OwnDeckContext, OwnDeckVariant};
use serde_json::{json, Value};
use std::io::Read;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut text = String::new();
    std::io::stdin().read_to_string(&mut text)?;
    let mut input: Value = serde_json::from_str(&text)?;
    for case in input["cases"].as_array_mut().ok_or("missing cases")? {
        let variant: OwnDeckVariant = serde_json::from_value(case["variant"].clone())?;
        let hello = &case["hello"];
        let context = OwnDeckContext::from_original(variant, &hello["deck"], &hello["cards"]);
        case["expected_bits"] = json!(context
            .features
            .iter()
            .map(|x| x.to_bits())
            .collect::<Vec<_>>());
        case["expected"] = serde_json::to_value(context)?;
    }
    println!("{}", serde_json::to_string_pretty(&input)?);
    Ok(())
}
