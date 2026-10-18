//! Checkpoint-preserving bridge to tinygrad-generated cached C kernels.
use jepa_controller::{Encoded, Model, ModelRole};
use serde_json::Value;
use std::collections::{HashMap, HashSet};
use std::ffi::c_void;
use std::sync::Mutex;

const RAW: &[u8] = include_bytes!("../../../models/tx-t10.safetensors");
const EVALUATOR: &[u8] = include_bytes!("../../../models/tx-t10-e.safetensors");
const CONTEXT_META: &str = include_str!("../../generated/jepa_context.json");
const PREDICT_META: &str = include_str!("../../generated/jepa_predict4.json");
const TOKEN_LIMIT: usize = 24;
const TOKEN_DIM: usize = 21;
const STATE_DIM: usize = 73;
const ACTION_DIM: usize = 62;
const LATENT_DIM: usize = 96;
const KV_SIZE: usize = 4 * 25 * 16;
const BATCH: usize = 4;
const HORIZONS: [&str; 9] = [
    "1", "4", "s", "r:face", "r:trade", "r:hold", "r2:face", "r2:trade", "r2:hold",
];

// The local kernel objects were retargeted from host LLVM IR, retaining a
// 64-bit size_t setter index. Their network pointers use the wasm32 ABI.
#[cfg(target_arch = "wasm32")]
type SetterIndex = u64;
#[cfg(not(target_arch = "wasm32"))]
type SetterIndex = usize;

extern "C" {
    fn jepa_context_set_buf(index: SetterIndex, pointer: *const c_void);
    fn jepa_predict4_set_buf(index: SetterIndex, pointer: *const c_void);
    fn jepa_context_net(
        z: *mut f32,
        k0: *mut f32,
        v0: *mut f32,
        k1: *mut f32,
        v1: *mut f32,
        value: *mut f32,
        state: *const f32,
        ids: *const i32,
        features: *const f32,
        mask: *const f32,
    );
    fn jepa_predict4_net(
        latents: *mut f32,
        logits: *mut f32,
        z: *const f32,
        k0: *const f32,
        v0: *const f32,
        k1: *const f32,
        v1: *const f32,
        mask: *const f32,
        actions: *const f32,
        action_ids: *const i32,
        horizon: *const i32,
    );
}

// The generated programs have global scratch and binding tables. Guard binding
// and execution together, including when separate KernelModel instances exist.
static KERNEL_LOCK: Mutex<()> = Mutex::new(());

#[repr(C, align(16))]
#[derive(Clone, Copy)]
struct Float4([f32; 4]);

/// Heap storage whose first element satisfies generated float4 load alignment.
struct Floats {
    blocks: Vec<Float4>,
    len: usize,
}
impl Floats {
    fn zeros(len: usize) -> Self {
        Self {
            blocks: vec![Float4([0.0; 4]); len.div_ceil(4)],
            len,
        }
    }
    fn copy(values: &[f32]) -> Self {
        let mut out = Self::zeros(values.len());
        out.as_mut_slice().copy_from_slice(values);
        out
    }
    fn as_ptr(&self) -> *const f32 {
        self.blocks.as_ptr().cast()
    }
    fn as_mut_ptr(&mut self) -> *mut f32 {
        self.blocks.as_mut_ptr().cast()
    }
    fn as_slice(&self) -> &[f32] {
        // Float4 has exactly four f32 elements, no inter-block padding.
        unsafe { std::slice::from_raw_parts(self.as_ptr(), self.len) }
    }
    fn as_mut_slice(&mut self) -> &mut [f32] {
        unsafe { std::slice::from_raw_parts_mut(self.as_mut_ptr(), self.len) }
    }
    fn finite(&self) -> bool {
        self.as_slice().iter().all(|x| x.is_finite())
    }
}

#[repr(C, align(16))]
struct Ids24([i32; TOKEN_LIMIT]);
#[repr(C, align(16))]
struct Ids4([i32; BATCH]);

struct Binding {
    index: usize,
    name: String,
    bytes: usize,
}

#[derive(Debug, Default, Clone, Copy)]
pub struct KernelStats {
    pub context_calls: u64,
    pub predict_calls: u64,
    pub context_cache_hits: u64,
}

struct CachedContext {
    key: Vec<u32>,
    z: Floats,
    kv: [Floats; 4],
    mask: Floats,
    value: f32,
}

pub struct KernelModel {
    weights: [HashMap<String, Floats>; 2],
    context_bindings: Vec<Binding>,
    predict_bindings: Vec<Binding>,
    contexts: [Option<CachedContext>; 2],
    pub stats: KernelStats,
}

fn role_index(role: ModelRole) -> usize {
    match role {
        ModelRole::Raw => 0,
        ModelRole::Evaluator => 1,
    }
}

fn integer(value: &Value, label: &str) -> Result<usize, String> {
    value
        .as_u64()
        .and_then(|n| usize::try_from(n).ok())
        .ok_or_else(|| format!("invalid {label}"))
}

fn load_checkpoint(bytes: &[u8]) -> Result<HashMap<String, Floats>, String> {
    let raw_len: [u8; 8] = bytes
        .get(..8)
        .ok_or("truncated safetensors header")?
        .try_into()
        .map_err(|_| "invalid safetensors length")?;
    let header_len = usize::try_from(u64::from_le_bytes(raw_len))
        .map_err(|_| "safetensors header length overflow")?;
    let end = 8usize
        .checked_add(header_len)
        .ok_or("safetensors header length overflow")?;
    let header: Value =
        serde_json::from_slice(bytes.get(8..end).ok_or("truncated safetensors header")?)
            .map_err(|e| format!("invalid safetensors JSON: {e}"))?;
    let tensors = header
        .as_object()
        .ok_or("safetensors header is not an object")?;
    let data = bytes.get(end..).ok_or("truncated safetensors payload")?;
    let mut out = HashMap::new();
    let mut ranges = Vec::new();
    for (name, spec) in tensors {
        if name == "__metadata__" {
            continue;
        }
        if spec["dtype"].as_str() != Some("F32") {
            return Err(format!("{name}: expected F32 checkpoint tensor"));
        }
        let shape = spec["shape"]
            .as_array()
            .ok_or_else(|| format!("{name}: missing shape"))?;
        let count = shape.iter().try_fold(1usize, |n, v| {
            n.checked_mul(integer(v, "tensor shape")?)
                .ok_or_else(|| format!("{name}: shape overflow"))
        })?;
        let offsets = spec["data_offsets"]
            .as_array()
            .filter(|x| x.len() == 2)
            .ok_or_else(|| format!("{name}: invalid offsets"))?;
        let start = integer(&offsets[0], "tensor start")?;
        let stop = integer(&offsets[1], "tensor end")?;
        let length = count
            .checked_mul(4)
            .ok_or_else(|| format!("{name}: tensor length overflow"))?;
        if stop.checked_sub(start) != Some(length) {
            return Err(format!("{name}: shape and payload length differ"));
        }
        let payload = data
            .get(start..stop)
            .ok_or_else(|| format!("{name}: payload outside checkpoint"))?;
        let values: Vec<f32> = payload
            .chunks_exact(4)
            .map(|x| f32::from_le_bytes([x[0], x[1], x[2], x[3]]))
            .collect();
        if !values.iter().all(|x| x.is_finite()) {
            return Err(format!("{name}: nonfinite weight"));
        }
        ranges.push((start, stop));
        out.insert(name.clone(), Floats::copy(&values));
    }
    ranges.sort_unstable();
    if ranges.windows(2).any(|x| x[0].1 > x[1].0) {
        return Err("overlapping checkpoint tensors".into());
    }
    Ok(out)
}

fn load_bindings(
    text: &str,
    input_bytes: &[usize],
    output_bytes: &[usize],
) -> Result<Vec<Binding>, String> {
    let meta: Value =
        serde_json::from_str(text).map_err(|e| format!("invalid kernel manifest: {e}"))?;
    for (field, sizes) in [("inputs", input_bytes), ("outputs", output_bytes)] {
        let specs = meta[field]
            .as_array()
            .ok_or_else(|| format!("kernel {field} missing"))?;
        if specs.len() != sizes.len()
            || specs
                .iter()
                .zip(sizes)
                .any(|(v, n)| v["bytes"].as_u64() != Some(*n as u64))
        {
            return Err(format!("kernel {field} ABI size mismatch"));
        }
    }
    let specs = meta["bindings"]
        .as_array()
        .ok_or("kernel bindings missing")?;
    let mut seen = HashSet::new();
    let mut bindings = Vec::new();
    for spec in specs {
        let name = spec["name"]
            .as_str()
            .and_then(|s| s.strip_prefix("w."))
            .ok_or("kernel binding is not a checkpoint tensor")?
            .to_owned();
        if !seen.insert(name.clone()) {
            return Err(format!("duplicate kernel binding {name}"));
        }
        bindings.push(Binding {
            index: integer(&spec["index"], "binding index")?,
            name,
            bytes: integer(&spec["bytes"], "binding byte count")?,
        });
    }
    bindings.sort_unstable_by_key(|b| b.index);
    if bindings.iter().enumerate().any(|(i, b)| i != b.index) {
        return Err("noncontiguous kernel binding indices".into());
    }
    Ok(bindings)
}

fn validate_context(encoded: &Encoded) -> Result<(), String> {
    if encoded.state.len() != STATE_DIM
        || encoded.tokens.ids.len() != encoded.tokens.n
        || encoded.tokens.n.checked_mul(TOKEN_DIM) != Some(encoded.tokens.feats.len())
        || encoded.tokens.n > 32
    {
        return Err("encoded context shape mismatch".into());
    }
    if !encoded
        .state
        .iter()
        .chain(&encoded.tokens.feats)
        .all(|x| x.is_finite())
    {
        return Err("nonfinite encoded context".into());
    }
    if !encoded.tokens.ids.iter().all(|&id| (0..2048).contains(&id)) {
        return Err("card ID outside hash buckets".into());
    }
    Ok(())
}

fn context_key(encoded: &Encoded) -> Vec<u32> {
    let mut key =
        Vec::with_capacity(STATE_DIM + 1 + encoded.tokens.ids.len() + encoded.tokens.feats.len());
    key.extend(encoded.state.iter().map(|x| x.to_bits()));
    key.push(encoded.tokens.n as u32);
    key.extend(encoded.tokens.ids.iter().map(|&x| x as u32));
    key.extend(encoded.tokens.feats.iter().map(|x| x.to_bits()));
    key
}

impl KernelModel {
    pub fn new() -> Result<Self, String> {
        let weights = [load_checkpoint(RAW)?, load_checkpoint(EVALUATOR)?];
        let context_bindings = load_bindings(
            CONTEXT_META,
            &[292, 96, 2016, 96],
            &[384, 6400, 6400, 6400, 6400, 4],
        )?;
        let predict_bindings = load_bindings(
            PREDICT_META,
            &[384, 6400, 6400, 6400, 6400, 96, 992, 16, 4],
            &[1536, 16],
        )?;
        for bank in &weights {
            for binding in context_bindings.iter().chain(&predict_bindings) {
                let tensor = bank
                    .get(&binding.name)
                    .ok_or_else(|| format!("checkpoint missing {}", binding.name))?;
                if tensor.len.checked_mul(4) != Some(binding.bytes) {
                    return Err(format!(
                        "checkpoint binding size mismatch: {}",
                        binding.name
                    ));
                }
            }
        }
        Ok(Self {
            weights,
            context_bindings,
            predict_bindings,
            contexts: [None, None],
            stats: KernelStats::default(),
        })
    }

    fn bind(&self, role: usize, context: bool) {
        let bindings = if context {
            &self.context_bindings
        } else {
            &self.predict_bindings
        };
        for b in bindings {
            let ptr = self.weights[role][&b.name].as_ptr().cast();
            // Construction validates every size/name/index; storage stays alive
            // for this model's lifetime. Caller holds KERNEL_LOCK through execution.
            unsafe {
                if context {
                    jepa_context_set_buf(b.index as SetterIndex, ptr);
                } else {
                    jepa_predict4_set_buf(b.index as SetterIndex, ptr);
                }
            }
        }
    }

    fn ensure_context(&mut self, role: usize, encoded: &Encoded) -> Result<(), String> {
        validate_context(encoded)?;
        let key = context_key(encoded);
        if self.contexts[role].as_ref().is_some_and(|c| c.key == key) {
            self.stats.context_cache_hits += 1;
            return Ok(());
        }
        let used = encoded.tokens.n.min(TOKEN_LIMIT);
        let state = Floats::copy(&encoded.state);
        let mut ids = Ids24([0; TOKEN_LIMIT]);
        ids.0[..used].copy_from_slice(&encoded.tokens.ids[..used]);
        let mut feats = Floats::zeros(TOKEN_LIMIT * TOKEN_DIM);
        feats.as_mut_slice()[..used * TOKEN_DIM]
            .copy_from_slice(&encoded.tokens.feats[..used * TOKEN_DIM]);
        let mut cache = CachedContext {
            key,
            z: Floats::zeros(LATENT_DIM),
            kv: std::array::from_fn(|_| Floats::zeros(KV_SIZE)),
            mask: Floats::zeros(TOKEN_LIMIT),
            value: 0.0,
        };
        cache.mask.as_mut_slice()[..used].fill(1.0);
        let mut value = Floats::zeros(1);
        let _guard = KERNEL_LOCK
            .lock()
            .map_err(|_| "kernel execution lock poisoned")?;
        self.bind(role, true);
        unsafe {
            jepa_context_net(
                cache.z.as_mut_ptr(),
                cache.kv[0].as_mut_ptr(),
                cache.kv[1].as_mut_ptr(),
                cache.kv[2].as_mut_ptr(),
                cache.kv[3].as_mut_ptr(),
                value.as_mut_ptr(),
                state.as_ptr(),
                ids.0.as_ptr(),
                feats.as_ptr(),
                cache.mask.as_ptr(),
            );
        }
        self.stats.context_calls += 1;
        if !cache.z.finite() || !cache.kv.iter().all(Floats::finite) || !value.finite() {
            return Err("nonfinite context kernel output".into());
        }
        cache.value = value.as_slice()[0];
        self.contexts[role] = Some(cache);
        Ok(())
    }
}

impl Model for KernelModel {
    fn predict_values(
        &mut self,
        role: ModelRole,
        encoded: &Encoded,
        horizon: &str,
    ) -> Result<Vec<f64>, String> {
        let hi = HORIZONS
            .iter()
            .position(|&x| x == horizon)
            .ok_or_else(|| format!("unsupported horizon {horizon}"))? as i32;
        let count = encoded.actions.n;
        if encoded.actions.ids.len() != count
            || count.checked_mul(ACTION_DIM) != Some(encoded.actions.rows.len())
        {
            return Err("encoded actions shape mismatch".into());
        }
        if !encoded.actions.rows.iter().all(|x| x.is_finite())
            || !encoded.actions.ids.iter().all(|&x| (0..2048).contains(&x))
        {
            return Err("invalid encoded actions".into());
        }
        if count == 0 {
            return Ok(Vec::new());
        }
        let ri = role_index(role);
        self.ensure_context(ri, encoded)?;
        let cache = self.contexts[ri]
            .as_ref()
            .ok_or("context cache unavailable")?;
        let mut actions = Floats::zeros(BATCH * ACTION_DIM);
        let mut ids = Ids4([0; BATCH]);
        let mut latents = Floats::zeros(BATCH * LATENT_DIM);
        let mut logits = Floats::zeros(BATCH);
        let mut result = Vec::with_capacity(count);
        let _guard = KERNEL_LOCK
            .lock()
            .map_err(|_| "kernel execution lock poisoned")?;
        self.bind(ri, false);
        for start in (0..count).step_by(BATCH) {
            let n = (count - start).min(BATCH);
            actions.as_mut_slice().fill(0.0);
            actions.as_mut_slice()[..n * ACTION_DIM].copy_from_slice(
                &encoded.actions.rows[start * ACTION_DIM..(start + n) * ACTION_DIM],
            );
            ids.0.fill(0);
            ids.0[..n].copy_from_slice(&encoded.actions.ids[start..start + n]);
            unsafe {
                jepa_predict4_net(
                    latents.as_mut_ptr(),
                    logits.as_mut_ptr(),
                    cache.z.as_ptr(),
                    cache.kv[0].as_ptr(),
                    cache.kv[1].as_ptr(),
                    cache.kv[2].as_ptr(),
                    cache.kv[3].as_ptr(),
                    cache.mask.as_ptr(),
                    actions.as_ptr(),
                    ids.0.as_ptr(),
                    &hi,
                );
            }
            self.stats.predict_calls += 1;
            if !latents.finite() || !logits.finite() {
                return Err("nonfinite prediction kernel output".into());
            }
            result.extend(logits.as_slice()[..n].iter().map(|&x| f64::from(x)));
        }
        Ok(result)
    }

    fn context_value(&mut self, role: ModelRole, encoded: &Encoded) -> Result<f64, String> {
        let ri = role_index(role);
        self.ensure_context(ri, encoded)?;
        Ok(f64::from(
            self.contexts[ri]
                .as_ref()
                .ok_or("context cache unavailable")?
                .value,
        ))
    }

    fn has_horizon(&self, _role: ModelRole, horizon: &str) -> bool {
        HORIZONS.contains(&horizon)
    }
}
