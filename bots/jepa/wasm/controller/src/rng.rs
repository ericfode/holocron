//! Python random.Random's integer seeding and randrange, as used by the JS port.
#[derive(Clone)]
pub struct PyRandom {
    mt: [u32; 624],
    at: usize,
}
impl PyRandom {
    pub fn new(seed: u64) -> Self {
        let mut r = Self {
            mt: [0; 624],
            at: 624,
        };
        r.seed(seed);
        r
    }
    pub fn seed(&mut self, seed: u64) {
        let key = if seed > u32::MAX as u64 {
            vec![seed as u32, (seed >> 32) as u32]
        } else {
            vec![seed as u32]
        };
        self.mt[0] = 19650218;
        for i in 1..624 {
            let p = self.mt[i - 1] ^ (self.mt[i - 1] >> 30);
            self.mt[i] = 1812433253_u32.wrapping_mul(p).wrapping_add(i as u32);
        }
        let (mut i, mut j) = (1, 0);
        for _ in 0..624.max(key.len()) {
            let p = self.mt[i - 1] ^ (self.mt[i - 1] >> 30);
            self.mt[i] = (self.mt[i] ^ p.wrapping_mul(1664525))
                .wrapping_add(key[j])
                .wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= 624 {
                self.mt[0] = self.mt[623];
                i = 1;
            }
            if j >= key.len() {
                j = 0;
            }
        }
        for _ in 0..623 {
            let p = self.mt[i - 1] ^ (self.mt[i - 1] >> 30);
            self.mt[i] = (self.mt[i] ^ p.wrapping_mul(1566083941)).wrapping_sub(i as u32);
            i += 1;
            if i >= 624 {
                self.mt[0] = self.mt[623];
                i = 1;
            }
        }
        self.mt[0] = 0x80000000;
        self.at = 624;
    }
    pub fn uint32(&mut self) -> u32 {
        if self.at >= 624 {
            for k in 0..624 {
                let y = (self.mt[k] & 0x80000000) | (self.mt[(k + 1) % 624] & 0x7fffffff);
                self.mt[k] =
                    self.mt[(k + 397) % 624] ^ (y >> 1) ^ if y & 1 != 0 { 0x9908b0df } else { 0 };
            }
            self.at = 0;
        }
        let mut y = self.mt[self.at];
        self.at += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c5680;
        y ^= (y << 15) & 0xefc60000;
        y ^= y >> 18;
        y
    }
    pub fn below(&mut self, n: usize) -> usize {
        assert!(
            n > 0 && (n as u64) <= (1_u64 << 32),
            "empty or oversized randrange"
        );
        let bits = usize::BITS - n.leading_zeros();
        let shift = 32_i32 - bits as i32;
        loop {
            let raw = self.uint32();
            let x = if shift > 0 { raw >> shift } else { raw } as usize;
            if x < n {
                return x;
            }
        }
    }
    pub fn choice(&mut self, xs: &[usize]) -> usize {
        xs[self.below(xs.len())]
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn python_seed_zero() {
        let mut r = PyRandom::new(0);
        assert_eq!(
            (0..5).map(|_| r.uint32()).collect::<Vec<_>>(),
            vec![3626764237, 1654615998, 3255389356, 3823568514, 1806341205]
        );
    }
}
