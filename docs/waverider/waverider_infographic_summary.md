# WaveRider Algorithm — Infographic Summary

**For use with Paper (paper.dropbox.com) infographic creation**

Author: Eric G. Suchanek, PhD
proteusPy Project — https://github.com/suchanek/proteusPy

---

## One-Liner

**WaveRider projects out 99% of gradient noise before running Adam, by discovering the low-dimensional manifold the loss landscape actually lives on.**

---

## The Core Problem (Panel 1)

**Adam treats all dimensions equally — but most dimensions are noise.**

- A 243-parameter neural network has 243 gradient dimensions
- Only 2–3 of those dimensions carry optimization signal
- The other 240 dimensions are pure mini-batch noise
- Standard Adam wastes momentum and adaptive state on those noise dimensions

**Visual:** A 3D cube of gradient arrows, most grayed out (noise), 2–3 highlighted red (signal).

---

## The Key Insight (Panel 2)

**The loss landscape lives on a thin, curved manifold inside the high-dimensional weight space.**

- Sample gradients from different mini-batches at the same point
- PCA reveals which directions the gradient *actually varies* along
- Those directions = the manifold tangent space (signal)
- Everything else = mini-batch noise that averages to zero

**Visual:** A curved 2D surface (manifold) embedded in a 3D space. Arrows on the surface = signal. Arrows pointing off the surface = noise.

---

## The Algorithm (Panel 3) — 5 Steps

### Step 1: Sample Gradient Diversity
```
Sample S mini-batch gradients at current weights w:
  g₁, g₂, ..., gₛ  (S ≈ 40 random subsets)
```
**What:** Compute gradients on different random subsets of training data.
**Why:** Reveals which gradient directions are consistent (signal) vs. random (noise).

### Step 2: Discover the Manifold via PCA
```
PCA of {g₁, ..., gₛ} → eigenvalues λ₁ ≥ λ₂ ≥ ... ≥ λₚ
Keep top d eigenvectors capturing τ = 90% of variance
  → d ≈ 2–3 (out of P = 243)
```
**What:** Find the d directions where the gradient actually varies.
**Why:** These d directions span the tangent space of the loss manifold.

### Step 3: Project Gradient onto Manifold
```
Full gradient:  g ∈ R^P  (all P dimensions)
Local coords:   ℓ = Vd^T g ∈ R^d  (only d dimensions)
Projected:      g_proj = Vd ℓ ∈ R^P  (off-manifold zeroed)
```
**What:** Keep only the manifold-aligned part of the gradient.
**Why:** Eliminates noise *before* it enters Adam's state.

### Step 4: Adam Update on Clean Gradient
```
m ← β₁ m + (1 - β₁) g_proj     (momentum on clean signal)
v ← β₂ v + (1 - β₂) g_proj²    (adaptive LR on clean signal)
Δw = m̂ / (√v̂ + ε)              (bias-corrected Adam step)
```
**What:** Standard Adam, but fed manifold-projected gradients.
**Why:** Momentum accumulates signal only. Adaptive denominator tracks signal variance only.

### Step 5: Step and Re-orient
```
w ← w - η Δw
Every R epochs: re-sample gradients, re-compute PCA
Adam state (m, v) persists across re-orientations
```
**What:** Move the weights and periodically update the manifold estimate.
**Why:** The manifold rotates as training progresses; the optimizer must track it.

---

## Key Numbers (Panel 4)

| Metric | Value |
|--------|-------|
| Weight space dimensions (P) | 243 |
| Intrinsic manifold dimensions (d) | 2–3 |
| Noise dimensions suppressed | 240 (98.9%) |
| Adam state variables (standard) | 486 (2 × P) |
| Adam state doing useful work | ~6 (2 × d) |

---

## The Architecture Stack (Panel 5)

```
WaveRider (ManifoldAdamWalker)
  │
  ├── Gradient-Diversity PCA
  │     Mini-batch gradient sampling → eigendecomposition
  │     → intrinsic dimensionality d, tangent basis Vd
  │
  ├── Manifold Projection
  │     g → Vd Vd^T g  (project, suppress, reconstruct)
  │
  ├── Adam Core
  │     Momentum (m) + Adaptive LR (v) on projected gradients
  │     State persists across manifold re-orientations
  │
  └── TurtleND
        N-dimensional coordinate frame
        Givens rotations, orthonormal basis maintenance
        Origin: Turtle3D for molecular modeling (Pabo & Suchanek, 1986)
```

---

## Why It Works — Three Sentences

1. **Mini-batch gradients vary along a tiny subspace** — PCA finds it.
2. **Projecting before Adam means momentum never accumulates noise** and the adaptive denominator only tracks real curvature.
3. **The result is Adam operating in a 100x smaller space** where every dimension carries signal.

---

## The Lineage (Panel 6 — Timeline)

```
1982  Logo Turtle — 2D, pen on paper, Spirographs
  ↓
1986  Turtle3D — 3D coordinate frames, molecular modeling
  ↓        (Pabo & Suchanek, Biochemistry 1986)
  ↓
2024  TurtleND — N-dimensional Givens rotations
  ↓
2024  ManifoldWalker — Local PCA + gradient projection
  ↓
2024  ManifoldAdamWalker (WaveRider) — Adam in the tangent space
  ↓
2024  ManifoldModel — The manifold IS the model (no weights)
```

---

## Comparison: Adam vs WaveRider (Panel 7)

```
ADAM                              WAVERIDER
────────────────────              ────────────────────
Gradient: all P dims              Gradient: projected to d dims
Momentum: signal + noise          Momentum: signal only
Adaptive LR: tracks noise var     Adaptive LR: tracks signal var
State: 2P variables               State: 2P vars, ~2d active
Treats space as isotropic         Discovers anisotropic manifold
```

---

## Formula Card (Panel 8 — for the math-inclined)

**Gradient-Diversity PCA:**
```
G = [g₁ - ḡ, ..., gₛ - ḡ]^T
C = G^T G / (S-1) = VΛV^T
d = min{j : Σᵢ₌₁ʲ λᵢ / Σλ ≥ τ}
```

**Manifold-Projected Adam Step:**
```
g_proj = Vd Vd^T g          (project)
m ← β₁m + (1-β₁)g_proj     (first moment)
v ← β₂v + (1-β₂)g_proj²    (second moment)
w ← w - η m̂/(√v̂ + ε)      (step)
```
