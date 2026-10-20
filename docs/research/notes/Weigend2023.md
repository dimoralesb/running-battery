# Weigend2023: A hydraulic model beats W′ balance models for recovery
Citation: Weigend FC, Clarke DC, Obst O, Siegler J. A hydraulic model outperforms work-balance models for predicting recovery kinetics from intermittent exercise. Ann Oper Res 2023;325:589–613. doi:10.1007/s10479-022-04947-2 (open access; preprint arXiv:2108.04510). Code: github.com/faweigend/pypermod.
Type: method / model comparison (retrospective, on published data)
Context: group-average recovery ratios extracted from 5 cycling studies (Bartram 2018, Caen 2019/2021, Chidnok, Ferguson 2010, Weigend 2021). All after **full** exhaustion.
Evidence strength: medium for "hydraulic fits recovery data better than one-pool W′ balance in cycling"; low for football (no running, no partial depletion).

## Definitions and thresholds
- W′BAL-ODE (Skiba 2015) with three τ choices: Skiba τ = W′/D_CP; Bartram τ (elite cyclists, faster); a new τ fitted to the same data (τ = 1274.45·e^(−0.0308·D_CP) + 266.65, R² 0.14) (Section 2.1.3).
- Generalised Margaria–Morton hydraulic model: three tanks (aerobic infinite, anaerobic fast, anaerobic slow), **8 parameters**, fitted by evolutionary computation from CP and W′ plus a fixed set of recovery ratios.

## Key numbers   (each with page/table/figure)
- Prediction error: **MAE 7.11 (SD 6.83) hydraulic vs 24.87 (SD 14.35) W′bart**, RMSE 9.69 vs 28.46 (p < .001) (Section 3.6, Table 6).
- vs W′skib and W′weig: hydraulic MAE 7.07, RMSE 9.94; AICc 151.85 (hydraulic, k = 8) vs 181.03 (W′weig, k = 3) (Section 3.6).
- Data-set level: hydraulic best on Bartram (MAE 6.96 vs 18.74 skib) and Caen (3.52); **W′skib best on Chidnok (9.4), W′weig best on Ferguson (6.7)** (Section 4.1). No model wins everywhere.
- Example (Table 1, Bartram elite cyclist CP 393 W, W′ 23.3 kJ, 60 s recovery at 293 W): observed 47%, W′skib 22.8%, hydraulic 44.8%.
- W′BAL-ODE recovery does not depend on how hard the previous effort was; the hydraulic model does (Fig. 9).
- Fitting cost: **≥3 h on 7 CPU cores per CP/W′ combination** (Section 4.2).
- Hydraulic model predicts some recovery while exercising **at** CP (controversial) (Section 4.2).

## Equations
Hydraulic ODEs are in Weigend 2021 (not in our corpus). ODE form as in Skiba2021. Not checked against PDF images.

## Limitations
- Cycling, group means, full exhaustion only.
- Bartram "observations" are themselves model predictions.
- Expensive fitting; 8 parameters with no football meaning.

## Use in Running Battery
- Simulator: **optional second truth model** (stretch goal). Fit once for a "typical player" (scaled CP/W′ → CS/D′), then run some synthetic matches with hydraulic truth to show our one-pool estimator still tracks fatigue when the truth model is different. Fitting time makes per-player fits impractical in 13 days.
- Fatigue estimator: no.
- Agents / claims: none.
- Overlay / UI: the three-tank picture is a nice explainer graphic for analyst mode.

## Ideas or questions it raised
- pypermod may ship pre-fitted configurations; check before fitting anything.
