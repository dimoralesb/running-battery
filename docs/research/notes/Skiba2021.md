# Skiba2021: The W′ balance model, mathematical and methodological considerations
Citation: Skiba PF, Clarke DC. The W′ balance model: mathematical and methodological considerations. Int J Sports Physiol Perform 2021;16(11):1561–1572. doi:10.1123/ijspp.2021-0205
Type: review (narrative, by the model's authors)
Context: theory paper; examples are cycling (power meters, 1 Hz). No new data.
Evidence strength: high as the authoritative description of the model and its limits; it is not a validation study.

## Definitions and thresholds
- **W′BAL-INT** (integral form, Skiba 2012): W′ remaining = W′₀ minus the convolution of W′ expended with an exponential recovery kernel, τ from the 2012 fitted equation (τ = 546·e^(−0.01·D_CP) + 316). Assumes some recovery is always going on, even during depletion.
- **W′BAL-ODE** (differential form, Skiba 2015, derived by Clarke): depletes at (P − CP) when P > CP; recovers when P < CP at a rate proportional to (CP − P) and to the fraction of W′ missing. Its apparent time constant is **W′₀ / D_CP**. No parameter fitting needed. Depletion and recovery never happen at the same time.
- **W′BAL-KODE**: ODE form with a constant K that raises effective CP during intermittent work (K = 1.28 matched the INT form in one example).
- **W′BAL-MULTI**: two-compartment version of the INT form (gains k₁, k₂; time constants τ₁, τ₂). Proposed in 2012, never formally studied.

## Key numbers   (each with page/table/figure)
- Worked example for software checks (Table 1): CP 245 W, W′₀ 14,000 J, 300 W for 19 s then 20 W. ODE: 12,955 J left at s19, 12,971.66 J at s20, 12,988.06 J at s21. INT (τ 373.55 s): 12,979.77 J at s19. **Use as a unit test for our D′ balance code** (swap W for m/s and J for m).
- ODE vs data (Table 2, Ferguson et al. group data, CP 213 W, W′ 21.6 kJ): ODE implies τ = 112 s, a simple fit to the data gives 336 s. ODE predicted 14.1 kJ recovered at 120 s vs 7.8 kJ measured: **ODE recovers about 3× too fast in that cycling dataset**.
- In a 60 s on / 30 s off example, ODE predicted exhaustion ~300 s earlier than INT (Fig. 5A).
- Typical error of W′ estimates: **7–20%**, one report 46% (PDF p.7 = journal p.1567).
- Exhaustion does not happen exactly at W′BAL = 0; both forms "oscillate around zero" before real exhaustion (PDF p.7 = journal p.1567).
- Galbraith et al.: INT form with the cycling τ failed for intermittent running; it worked better when τ was fitted to the runner's own data (PDF p.4 = journal p.1564).

## Equations
Not in the docling .md (all equations dropped). Forms above are from the text; the ODE recovery law matches what we use (synthesis §3.2.2). Checked conceptually against the text, not against equation images.

## Limitations
- Review, cycling-centred; no running or team-sport data.
- Neither form is clearly better on data; authors recommend running both and picking the one that fits the situation.
- τ should be individual and mode-specific; the group equation does not generalise (Bartram elite cyclists faster, Skiba's own pros slower).

## Use in Running Battery
- Simulator: nothing new for parameters. Supports keeping a two-compartment truth as a plausible physiology.
- Fatigue estimator: **our estimator is the ODE form.** Implement it exactly, test it against Table 1, and remember it may recover too fast in some data and predict exhaustion too early in hard intermittent work.
- Agents / claims: "battery at 0%" must never be stated as "exhausted". Even in the lab the model only gets near zero. Put an uncertainty band of at least ±10–20% of D′ on the battery (W′ error 7–20%).
- Overlay / UI: show the battery as a band, not a sharp line (fits Buchheit2015 uncertainty display).

## Ideas or questions it raised
- KODE idea (CP effectively higher during intermittent work) could explain why football players rarely empty the battery [Sutcliffe2025].
