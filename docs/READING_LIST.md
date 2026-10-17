# Reading List: Fatigue Model

Papers are referenced by key (e.g. `[Mohr2003]`) in all project docs. The files keep their Zotero names; the [Paper files](#paper-files) table at the end maps each key to its file. Each paper exists as `docs/papers/md/<file>.md` (docling) and `docs/papers/pdf/<file with spaces>.pdf` (use the PDF to check equations and tables).

✅ = journal, authors and year checked online (Crossref / PubMed) on 2026-10-14. The rest are classic papers listed from memory: confirm details in Zotero.

## Source quality rule

| Accept | Use with care | Exclude |
|---|---|---|
| Established peer-reviewed sports science journals: J Sports Sci, Med Sci Sports Exerc, Int J Sports Physiol Perform, Int J Sports Med, Sports Med, Eur J Sport Sci, J Sci Med Sport, J Biomech, Biology of Sport, Int J Sports Sci Coach. Nature-family (Sci Rep, Sci Data). | **PLOS ONE**, small regional journals: check sample size and methods. **MIT Sloan conference papers**: industry standard for analytics methods but not classic peer review; cite for methods only. **arXiv preprints**: methods only, always labelled "preprint". | **MDPI** journals (*Sports*, *Applied Sciences*, *IJERPH*…). **Frontiers**: only if nothing better exists. |

Prefer **recent** papers for numbers (match demands have changed: Premier League high-intensity running rose ~30% between 2006 and 2013 (Barnes 2014, cited by [Allen2024]), and a further +12% high-speed and +15% sprint distance from 2014/15 to 2018/19 [Allen2024, Table 4]). Older papers are fine for **methods and equations**, which don't age (e.g. W′ balance, metabolic power).

---

## A. Recent evidence (2020–2026): read these first

| Key | Paper | Why | Extract |
|---|---|---|---|
| ✅ **Leifsson2024** | Leifsson EN, Krustrup P, Mohr M, Randers MB (2024). *Effect of peak intensity periods on temporary fatigue and recovery kinetics in professional male football.* J Sports Sci 42(9):769–775. doi:10.1080/02640414.2024.2364135 | **The modern update of Mohr2003, by the same group.** 479 players, 3 Danish Superliga seasons, rolling averages. After a peak period, high-speed running drops by up to 45% in the next minute (vs the match average). It recovers over ~5 min after **5-min** peaks, but within 2–3 min after 1–2-min peaks. Sprint recovers more slowly (still −12% at minute 5). **Acceleration distance is higher** after **acceleration** peaks: accelerations cluster in busy phases. | Minute-by-minute recovery curves after peak 1-, 2-, 5-min periods for high-speed running (≥5.5 m/s), sprint (≥7 m/s), accelerations (≥3 m/s²). **This is the shape of our "battery recovery."** |
| ✅ **Schimpchen2020** | Schimpchen J, Gopaladesikan S, Meyer T (2021). *The intermittent nature of player physical output in professional football matches: an analysis of sequences of peak intensity and associated fatigue responses.* Eur J Sport Sci 21(6):793–802. doi:10.1080/17461391.2020.1776400 | A young **second-tier** Portuguese team, full season, 10 Hz GPS, high intensity ≥5.0 m/s (18 km/h). Total distance recovers within 3 min of a peak, but **high-intensity distance stays 64–89% lower in the first minute** (vs the match mean including the peak) and is still 20–31% lower at minute 5 after 1- and 5-min peaks (the 6% after 10-min peaks is not significant). High-intensity peaks don't depend on score or match time. | Confirms the fatigue is **specific to high-intensity running**, not to total distance. The model must track high-speed efforts separately. |
| ✅ **Mizelman2024** | Mizelman E, Pearson A, Chu D, Clarke DC (2024). *Critical speed models of high-resolution speed-duration profiles describe peak running demands in soccer.* Int J Sports Sci Coach 19:2056–2066. doi:10.1177/17479541241246951 | **Estimates critical speed and D′ from match/training GPS data, without a lab test.** That is exactly our situation. D′ around 79–106 m depending on model. | Which CS model fits best; the speed–duration profile method. **Not our default player parameters:** the authors say match-fitted CS (about 2 m/s [7.2 km/h]) is "likely well below" true CS (p.2064). |
| ✅ **Morin2021** | Morin JB, Le Mat Y, Osgnach C, Barnabò A, Pilati A, Samozino P, di Prampero PE (2021). *Individual acceleration-speed profile in-situ: a proof of concept in professional football players.* J Biomech 123:110524. doi:10.1016/j.jbiomech.2021.110524 | Gets each player's max acceleration and top speed from **training GPS** data, at least 5 sessions (linear relationship, R² > 0.98). Matches were not tested. | The method to build each player's acceleration–speed profile. Used in the simulator (player capabilities). Not used for in-match fatigue: one match is not enough [AlonsoCallejo2024]. |
| ✅ **Bou2026** (preprint) | Bou X, Correger N, Cloots A, Gavage C, Giancola S, Schwartz C, Delvaux F, Cloots R, Van Droogenbroeck M, Cioppa A (2026). *Towards athlete fatigue assessment from association football videos.* arXiv:2604.05636 | **Very close to our idea:** fatigue indicators from acceleration–speed profiles, computed from broadcast video tracking (SoccerNet). Published April 2026. | How they turn A-S profiles into fatigue indicators; limits from noisy tracking. Also shows the topic is current. |
| ✅ **Allen2024** | Allen T, Taberner M, Zhilkin M, Rhodes D (2024). *Running more than before? The evolution of running load demands in the English Premier League.* Int J Sports Sci Coach 19:779–787. doi:10.1177/17479541231164507 | **Premier League**, 2014/15 to 2018/19. Distance, high-intensity and sprint distance increased. | Current Premier League team and position values. Replaces Bradley2009 for numbers. |
| ✅ **Kavanagh2024** | Kavanagh R, Di Michele R, Oliveira R, McDaid K, Rhodes D, Morgans R (2024). *The relationships between distances covered above generic and relative speed thresholds by male soccer players in English Premier League matches across two competitive seasons.* Biol Sport. PMC11474994 | **Premier League, one club** (16 players, Second Spectrum 25 Hz). Generic thresholds (same for everyone) vs. relative thresholds (% of each player's top speed). | Whether we should use the same speed thresholds for all players or per-player thresholds. |
| ✅ **Morgans2025** | Morgans R, Mandorino M, Beato M, Ryan B, Zmijewski P, Moreira A (2025). *Contextualized high-speed running and sprinting during English Premier League match-play with reference to possession, positional demands and opponent ranking.* Biol Sport. PMC12244393 | **Premier League, one club** (31 players, Second Spectrum 25 Hz). High-speed running by position, in and out of possession, by opponent. No total distance. | Values for the simulator per position and phase. Context factors for the agents. |
| ✅ **Bortnik2022** | Bortnik L, Burger J, Rhodes D (2022). *The mean and peak physical demands during transitional play and high pressure activities in elite football.* Biol Sport 39(4):1055–1064. DOI printed in the PDF: 10.5114/biolsport.2023.112968 | **Transitions are the most demanding moments** (vs the 90-min average). Losing the ball (negative transition) has the highest **total distance** and accelerations plus decelerations; **positive transitions have the most sprinting**. One Polish team, GPS. | Demands of transitions and pressing. This is where tired players get exposed: our key "tired moment" scenario. |
| ✅ **SilvaH2025** | Silva H, Nakamura FY, Racil G, Gómez-Diaz A, Menezes P, Chamari K, Marcelino R (2025). *Peak match sprinting speed during soccer matches: analysing the pre- and post-peak speed dynamics.* Biol Sport 42(1):193–200. doi:10.5114/biolsport.2024.136089. PMC11694206 | What happens to speed before and after a player's top sprint. | The shape of a sprint (build-up and braking within the same run) for the motion model. The speed drop after the peak is braking, **not fatigue**. |
| ✅ **daSilva2025** | da Silva MF, Novillo A, Aleta A, Lopez del Campo R, Resta R, Moreno Y, Buldú JM (2025). *Interplay between pitch control and top speed in soccer: the stamina factor.* Sci Rep 15:38799. arXiv:2504.18250 | **Links stamina to the space a player controls.** LaLiga tracking. | How a lower top speed reduces pitch control (logarithmic effect). The "stamina factor" is a **hypothetical multiplier** swept over a team, not measured fatigue. Our pitch-control model and its settings. |
| ✅ **Bassek2025** | Bassek M, Rein R, Weber H, Memmert D (2025). *An integrated dataset of spatiotemporal and event data in elite soccer.* Sci Data 12. doi:10.1038/s41597-025-04505-y | Our main open dataset (CC BY 4.0). | Data format and how to download it. |
| ✅ **Modric2020** | Modric T, Versic S, Sekulic D (2020). *Aerobic fitness and game performance indicators in professional football players; playing position specifics and associations.* Heliyon 6(11):e05427. doi:10.1016/j.heliyon.2020.e05427 | **Directly measured aerobic fitness of professionals by position** (treadmill, gas exchange). Our "pro" typical player. | 16 Croatian first-division players, tested after the off-season break, 2% incline (Table 1, **computed over 82 game performances, not 16 players: the SDs are not clean between-player SDs**): VO₂max 57.8 / 57.7 / 56.7 ml/kg/min (defenders / midfielders / forwards); anaerobic threshold 4.44 / 4.57 / 4.29 m/s (16.0 / 16.5 / 15.5 km/h), SD 0.21–0.26 m/s, at 90–93% of VO₂max; aerobic threshold 3.73 / 3.98 / 3.38 m/s. **The forwards' aerobic threshold is 12.81 km/h in the text and 12.18 in Table 1.** One team, small sample. |
| ✅ Kramer2018 | Kramer M, Clark IE, Jamnick N, Strom C, Pettitt RW (2018). *Normative data for critical speed and D′ for high-level male rugby players.* J Strength Cond Res 32(3):783–789. doi:10.1519/JSC.0000000000001880 | The only measured D′ for a high-level field-team sport we found. | 30 South African high-level rugby players, GPS 3MT: CS 3.87 ± 0.55 m/s, **D′ 288.2 ± 49.1 m**, 13 of 30 above 300 m (abstract). Not downloaded; abstract only. |
| ✅ Carpels2026 | Carpels T, Kemi OJ (2026). *Physical profiling in elite professional men's football: academy, reserve and first team variations in fitness and performance.* Open Access J Sports Med 17(1):2697533. doi:10.1080/11791543.2026.2697533 | A clean between-player spread of aerobic fitness in a professional first team. Use with care (small open-access journal). | Scottish Premiership first team (Europa League), n = 25: VO₂max 56.3 ± 3.6 ml/kg/min, estimated from the 30-15 IFT with Buchheit's equation (Table 1, read from the web page). Not downloaded. |
| ✅ Xu2026 | Xu H, Li T, Xing W, Zhu J, Zhang Z, Chen Z (2026). *Comparative effectiveness of training interventions on VO2max in male soccer players: a systematic review and network meta-analysis.* BMC Sports Sci Med Rehabil 18:457. doi:10.1186/s13102-026-01820-8 | Training effects on VO₂max, not reference values. | VO₂max is trainable within weeks (HIIT vs soccer training only: SMD 1.05, Table 1), so a pre-season club test drifts during the season. Cites youth maximal aerobic speed 4.08–4.61 m/s (U13–U16). Certainty of evidence low (CINeMA). |

## B. Foundational methods (older, but the equations are still used)

| Key | Paper | Why | Extract |
|---|---|---|---|
| Mohr2003 | Mohr M, Krustrup P, Bangsbo J (2003). *Match performance of high-standard soccer players with special reference to development of fatigue.* J Sports Sci 21(7):519–528. | The original evidence for temporary and end-of-match fatigue. Cite it as the origin; take numbers from Leifsson2024. | The concepts, plus the "last 15 min" decline. |
| Mohr2005 | Mohr M, Krustrup P, Bangsbo J (2005). *Fatigue in soccer: a brief review.* J Sports Sci 23(6):593–599. | When and why fatigue happens: after intense spells, start of 2nd half, end of match. | Mechanisms, for the agents' explanations. |
| Osgnach2010 | Osgnach C, Poser S, Bernardini R, Rinaldo R, di Prampero PE (2010). *Energy cost and metabolic power in elite soccer: a new match analysis approach.* Med Sci Sports Exerc 42(1):170–178. | Energy cost from speed **and** acceleration. | The equivalent-slope method and energy cost equation. |
| diPrampero2005 | di Prampero PE et al. (2005). *Sprint running: a new energetic approach.* J Exp Biol 208:2809–2816. | Physics behind Osgnach2010. | Only if Osgnach2010 is unclear. |
| Skiba2012 | Skiba PF, Chidnok W, Vanhatalo A, Jones AM (2012). *Modeling the expenditure and reconstitution of work capacity above critical power.* Med Sci Sports Exerc 44(8):1526–1532. | The W′ balance "battery" model. | W′bal equation and recovery time constant. We adapt power → speed (CS, D′). |
| Jones2017 | Jones AM, Vanhatalo A (2017). *The 'critical power' concept: applications to sports performance with a focus on intermittent high-intensity exercise.* Sports Med 47(Suppl 1):65–78. | Justifies critical power/speed for intermittent sports. | Limits of the model. |
| Spearman2017 | Spearman W, Basye A, Dick G, Hotovy R, Pop P (2017). *Physics-based modeling of pass probabilities in soccer.* MIT Sloan SAC. | Time-to-intercept model. Only σ and λ are fitted here; 5 m/s and 7 m/s² come from Spearman2018, and the 0.7 s reaction time from Shaw's code. | Equations, σ = 0.45 s and λ = 4.3 s⁻¹. |
| Spearman2018 | Spearman W (2018). *Beyond expected goals.* MIT Sloan SAC. | Pitch control. | Formulation. |
| Fernandez2018 | Fernández J, Bornn L (2018). *Wide open spaces.* MIT Sloan SAC. | Alternative pitch control. | Not used: it is simpler, but it has no top-speed or reaction parameter for fatigue to act on. |
| ✅ Narizuka2023 | Narizuka T, Takizawa K, Yamazaki Y (2023). *Validation of a motion model for soccer players' sprint by means of tracking data.* Sci Rep 13:865. doi:10.1038/s41598-023-27999-1 (preprint: arXiv:2205.04511) | Realistic sprint/motion model fitted on tracking data. | Motion equation for the simulator. |

## C. Fatigue → what changes on the pitch

Found via PubMed "cited by" for Carling2011 (69 citing papers) and Rampinini2008 (42). MDPI papers filtered out. All ✅.

### C1. Recent match studies (read these)

| Key | Paper | Finding | Extract |
|---|---|---|---|
| ✅ **Ju2022** | Ju W, Doran D, Hawkins R, Gómez-Díaz A, Martin-Garcia A, Ade JD, Laws A, Evans M, Bradley PS (2022). *Contextualised peak periods of play in English Premier League matches.* Biol Sport 39(4):973–983. doi:10.5114/biolsport.2022.112083 | **Premier League, 50 matches.** During peak periods, the biggest share of high-intensity distance is **recovery runs** (28–34% for players, 28–37% for teams). **After a peak, players do 22–44% less high-intensity "Covering" and 34–43% less "Recovery Run" out of possession, vs their match average** (p.975). The abstract's "20–53%" mixes these with team figures (Covering −20 to −41%, Recovery Run −32 to −53%). | **This is our core story, measured in the Premier League:** after an intense spell, players defend less. Use the numbers for the simulator and quote them in the pitch. |
| ✅ **Cortez2026** | Cortez A, Yousefian F, Folgado H, Brito J, Travassos B, Abade E, Liu H, Niu Z, Gonçalves B (2026). *Physical, tactical and technical performance of the most demanding passages of kinematic activity in elite soccer.* BMC Sports Sci Med Rehabil 18:195. doi:10.1186/s13102-026-01645-5 | **2022 World Cup (FIFA data).** In the minute after a peak passage, high-speed running is 93% lower **than in the peak minute** (not "below normal"). Technical variables are **counts only** (fewer passes and shots, not worse ones), and are confounded by ball in play falling from 82% to 57%. Defenders spend more time in their own third. | Technical and tactical changes after peaks, by position. "Technical decline" here means **fewer actions**, not **worse actions**. |
| ✅ **Fang2024** | Fang Z, Wang Z, Li X, Gómez MA, Liu H (2025). *Physical and technical performance in and after the worst-case scenario in matches of the Chinese Super League of soccer.* Biol Sport 42(2):95–103. doi:10.5114/biolsport.2025.142642 | **576 matches, 13,298 observations.** In the 5 min after the most intense 5 min: high-intensity running −77%, sprint −86% (both **vs the peak 5 min**, per ball-in-play minute). **Running with the ball and speed when receiving the ball drop. Other technical actions (passes, etc.) show only trivial changes.** | **The important nuance:** fatigue hits **physical-technical** actions (carrying, receiving at speed), not pass accuracy in general. Our simulator and agents should follow this. |
| ✅ Niu2026 | Niu Z, Wang Z, Wang Y, Iván-Baragaño I (2026). *Intra-positional technical performance under different physical demands in elite football: a comparison between most demanding passage and extremely demanding passage.* Front Physiol 17:1900931. doi:10.3389/fphys.2026.1900931 | 176 Chinese Super League matches. Compares technical actions **during** extreme vs ordinary peak passages (not after a peak). Effects depend on position: central midfielders lose the ball more and make fewer long passes. These are **counts** of successful passes; pass accuracy was not tested (so "central defenders improve short-pass accuracy" is wrong). | Position-specific effects. Frontiers journal: use with care, but the sample is large. |

### C2. Reviews

| Key | Paper | Finding | Extract |
|---|---|---|---|
| ✅ **Dambroz2022** | Dambroz F, Clemente FM, Teoldo I (2022). *The effect of physical fatigue on the performance of soccer players: a systematic review.* PLoS One 17(7):e0270099. | 12 studies. Physical fatigue harms passing, dribbling and kicking, and lowers sprint capacity. Effect on decisions (cognitive) is inconclusive. Tactical effects barely studied. | The summary sentence for our README. |
| ✅ Wang2024 | Wang B et al. (2024). *A systematic review of the factors that affect soccer players' short-passing ability, based on the Loughborough Soccer Passing Test.* BMC Sports Sci Med Rehabil 16:96. | 9 fatigue studies of a lab passing test. Claims that exhaustion "significantly worsens" short passing, but this is overstated: it counts votes across studies, and results are mixed and often not significant. | Size of the passing penalty (lab tests, not matches). |
| ✅ SilvaJR2018 | Silva JR, Rumpf MC, Hertzog M, Castagna C, Farooq A, Girard O, Hader K (2018). *Acute and residual soccer match-related fatigue: a systematic review and meta-analysis.* Sports Med 48(3):539–583. | 77 studies. At half-time, sprint performance already drops (effect size −0.3 to −1.0). | The half-time and end-of-match decline. |

### C3. Older experimental studies

| Key | Paper | Why | Extract |
|---|---|---|---|
| ✅ Rampinini2008 | Rampinini E, Impellizzeri FM, Castagna C, Azzalin A, Coutts AJ, Ferrari Bravo D, Wisløff U (2008). *Effect of match-related fatigue on short-passing ability in young soccer players.* Med Sci Sports Exerc 40(5):934–942. | Passing drops in a lab test after the match, but **in-match pass success did not drop** in the same study (75% → 79%, derived from Table 2). | Evidence for **no** pass-accuracy penalty in the simulator (PLAN decision 5). |
| ✅ Russell2011 | Russell M, Benton D, Kingsley M (2011). *The effects of fatigue on soccer skills performed during a soccer match simulation.* Int J Sports Physiol Perform 6(2):221–233. | Shooting precision and pass speed drop; dribbling doesn't. | Effect sizes per skill. |
| ✅ Carling2011 | Carling C, Dupont G (2011). *Are declines in physical performance associated with a reduction in skill-related performance during professional soccer match-play?* J Sports Sci 29(1):63–71. | Asks our exact question in **professional** matches. If the link is weak, we say so. | Their answer and in which situations. |
| Krustrup2006 | Krustrup P et al. (2006). *Muscle and blood metabolites during a soccer game: implications for sprint performance.* Med Sci Sports Exerc 38(6):1165–1174. | Physiology of temporary fatigue. | Sprint drop and recovery timing. |
| Akenhead2013 | Akenhead R, Hayes PR, Thompson KG, French D (2013). *Diminutions of acceleration and deceleration output during professional football match play.* J Sci Med Sport 16(6):556–561. | Accelerations decline over the match. Premier **Reserve** League (mean age 19.3 y), GPS 10 Hz, acceleration **distance** (not counts). | Decline per 15-min period. Its acceleration table doesn't add up; treat the low bands as doubtful. |

> **What the evidence supports (and what it doesn't).**
> - ✅ **Strong:** after an intense spell, high-intensity running drops sharply for a few minutes [Leifsson2024, Schimpchen2020, Fang2024, Cortez2026], and in the Premier League that includes **covering and recovery runs out of possession** [Ju2022].
> - ✅ **Strong:** actions that need speed (carrying the ball, receiving at speed) get worse after a peak [Fang2024].
> - ❌ **Not seen in matches:** a drop in pass accuracy. Lab tests show a drop [Rampinini2008 LSPT, Wang2024], but match studies show none [Fang2024; Carling2011; Rampinini2008 in-match]. [Niu2026] measured pass counts, not accuracy.
> - ❌ **Not established:** fatigue → individual tactical or decision errors [Dambroz2022].
>
> So the agents can say "*after that 2-minute pressing spell, he had much less in the tank for the recovery run*" (supported), but not "*he misplaced the pass because he was tired*" (not supported).

## C4. Peak timing (for the simulator)

| Key | Paper | Finding | Extract |
|---|---|---|---|
| ✅ Thoseby2022 | Thoseby B, Govus AD, Clarke AC, Middleton KJ, Dascombe BJ (2022). *Temporal distribution of peak running demands relative to match minutes in elite football.* Biol Sport 39(4):985–994. | Peaks of total distance and acceleration come early in each half; **peaks of high-speed running can happen at any time** (uniform distribution). | How to place intense spells across the match in the simulator. |
| ✅ Thoseby2023 | Thoseby B, Govus AD, Clarke AC, Middleton KJ, Dascombe BJ (2023). *Positional and temporal differences in peak match running demands of elite football.* Biol Sport 40(1):311–319. | Peak demands are lower in the second half for strikers (all metrics) and for acceleration in several positions. | Second-half peak reduction by position. |

## D. Limits and caveats

| Key | Paper | Why | Extract |
|---|---|---|---|
| ✅ Buchheit2015 | Buchheit M, Manouvrier C, Cassirame J, Morin JB (2015). *Monitoring locomotor load in soccer: is metabolic power, powerful?* Int J Sports Med 36(14):1149–1155. | GPS metabolic power underestimates real energy cost: 23 ± 10% during efforts in the Results (the abstract says 29%), ~85% in recovery. 14 youth players, 4 Hz GPS, low-speed circuit. | Error size. Shown as uncertainty in the UI. |
| Bradley2013 | Bradley PS, Noakes TD (2013). *Match running performance fluctuations in elite soccer: indicative of fatigue, pacing or situational influences?* J Sports Sci 31(15):1627–1638. | Less running is not always fatigue. | Situations where we must **not** call it fatigue. |
| Paul2015 | Paul DJ, Bradley PS, Nassis GP (2015). *Factors affecting match running performance of elite soccer players.* Int J Sports Physiol Perform 10(4):516–519. | Context factors. | Confounders for the simulator and agents. |
| Bangsbo2006 | Bangsbo J, Mohr M, Krustrup P (2006). *Physical and metabolic demands of training and match-play in the elite football player.* J Sports Sci 24(7):665–674. | Heart rate, %VO₂max and blood metabolites. No match energy expenditure, activity-change counts or sprint counts. | Only if we display an estimated effort. |
| Hills2018 | Hills SP et al. (2018). *Profiling the responses of soccer substitutes: a review of current literature.* Sports Med 48:2255–2269. | Fresh substitutes. | Substitute output vs. players replaced. |

## E. Lower priority

| Key | Paper | Note |
|---|---|---|
| ✅ Sutcliffe2025 | Sutcliffe DP, Kramer M (2025). PLOS ONE 20(6):e0323655. | D′ balance on match GPS, but only 26 university players. Test-based CS (~3.6 m/s) and D′ (173 ± 54 m) for our prior; battery dipped only 21 ± 6%. τ and the D′bal equation are **not reported**. Raw data on Harvard Dataverse (doi:10.7910/DVN/5FTIRQ; licence not checked). |
| ✅ Slimani2019 | Slimani M, Znazen H, Miarka B, Bragazzi NL (2019). *Maximum oxygen uptake of male soccer players according to their competitive level, playing position and age group: implication from a network meta-analysis.* J Hum Kinet 66:233–245. doi:10.2478/hukin-2018-0060 | Before 2020 and very heterogeneous (I² 93–98%), but the only pooled VO₂max data. VO₂max 58.2–62.2 ml/kg/min for professionals, ranges by level overlap (p.240); outfield positions do not differ (p.241: defenders 53.2–62.8, midfielders 54.7–63, forwards 54.5–62.9); match intensity about 80% of VO₂max (citing Reilly 2000, p.242; Bangsbo2006 says about 70%). Figures are effect sizes only. |
| ✅ Liu2021 | Liu KC, Sheard J, Frixou T, Milton P, Luna EP, Piatrikova E (2021). South African J Sports Med. PMC9924614 | Small regional journal, youth players. Optional. |
| ✅ Smith2018 | Smith MR, Thompson C, Marcora SM, Skorski S, Meyer T, Coutts AJ (2018). *Mental fatigue and soccer: current knowledge and future directions.* Sports Med 48(7):1525–1532. | Mental fatigue also hurts performance. Out of our scope (we can't measure it), but worth one line in the limitations. |
| ✅ Julian2021 | Julian R, Page RM, Harper LD (2021). *The effect of fixture congestion on performance during professional male soccer match-play.* Sports Med 51(2):255–273. | Playing two matches within 96 h has no clear effect on distance or technique. **Not downloaded or checked, so this claim is unverified.** We still don't model fatigue carried over from previous matches, and we say the support is unverified. |
| Bradley2009 | Bradley PS et al. (2009). J Sports Sci 27(2):159–168. | Premier League, but 2005/06 data. Use for speed thresholds only; numbers from Allen2024. |
| DiSalvo2007 | Di Salvo V et al. (2007). Int J Sports Med 28(3):222–227. | Old position profiles from the **Spanish league + Champions League** (Amisco 25 Hz), not the Premier League. Replaced by Allen2024 / Morgans2025. |

## F. Outside the source rule (read as exceptions, 2026-10-17)

Read on the user's request. Framing only: no calibration number comes from these. Cite with the qualifier shown.

| Key | Paper | Note |
|---|---|---|
| ✅ MarquesJimenez2017 | Marqués-Jiménez D, Calleja-González J, Arratibel I, Delextrat A, Terrados N (2017). *Fatigue and recovery in soccer: evidence and challenges.* Open Sports Sci J 10(Suppl 1: M5):52–70. doi:10.2174/1875399X01710010052 | Narrative review in a Bentham Open journal (publisher on Beall's list), 2017. Match numbers are second-hand (Bradley2009, Bradley2013) and partly miscopied, so cite the primary paper. Useful for: fatigue has many causes; players regulate their effort (p.55); responses differ between players, "individual analysis" (p.61); no agreed fatigue marker even with lab tests (p.56, p.58, Fig. 1). |
| ✅ Snyder2023 | Snyder BJ, Maung-Maung C, Whitacre C (2023). *Indicators of fatigue during a soccer match simulation using GPS-derived workload values: which metrics are most useful?* Sports 12(1):9 (online 27 Dec 2023). doi:10.3390/sports12010009 | **MDPI**, previously removed under the rule above. 20 women collegiate players, modified T-SAFT90 with 2–2.5 min breaks every 5 min. With imposed running, high-speed running falls from minute 15 (indirect evidence for pacing in matches); accelerometer load metrics don't change; jumps preserved. Several internal inconsistencies (notes). |

---

## Suggested reading order

1. **Leifsson2024, Schimpchen2020**: how temporary fatigue and recovery really look, minute by minute.
2. **Ju2022, Fang2024, Cortez2026**: what changes on the pitch after an intense spell (Premier League, Chinese Super League, World Cup).
3. **Mizelman2024, Morin2021**: what tracking data can and can't tell us about each player's capacity (match-fitted CS is not physiological; A–S profiles need ≥5 sessions).
4. **daSilva2025, Bortnik2022**: why it matters tactically (space, transitions).
5. **Allen2024, Morgans2025**: Premier League numbers for the simulator.
6. **Skiba2012, Osgnach2010**: the equations.
7. **Dambroz2022, Carling2011, Bradley2013, Buchheit2015**: the limits.

## Notes

Fill in as you read: key numbers, equations, page references.

## Paper files

Key → file name in `docs/papers/md/` (add `.md`). The PDF in `docs/papers/pdf/` has the same name with spaces instead of underscores.

| Key | File |
|---|---|
| Leifsson2024 | `Leifsson_et_al._-_2024_-_Effect_of_peak_intensity_periods_on_temporary_fatigue_and_recovery_kinetics_in_professional_male_foo` |
| Schimpchen2020 | `Schimpchen_et_al._-_2020_-_The_intermittent_nature_of_player_physical_output_in_professional_football_matches_An_analysis_of_s` |
| Mizelman2024 | `Mizelman_et_al._-_2024_-_Critical_speed_models_of_high-resolution_speed-duration_profiles_describe_peak_running_demands_in_so` |
| Morin2021 | `Morin_et_al._-_2021_-_Individual_acceleration-speed_profile_in-situ_A_proof_of_concept_in_professional_football_pl` |
| Bou2026 | `Bou_et_al._-_2026_-_Towards_Athlete_Fatigue_Assessment_from_Association_Football_Videos` |
| Allen2024 | `Allen_et_al._-_2024_-_Running_more_than_before_The_evolution_of_running_load_demands_in_the_English_Premier_League` |
| Allen2025 | `Allen_et_al._-_2025_-_Evolving_running_load_demands_and_fixture_congestion_in_the_English_Premier_League_a_decade_of_insi` |
| Allen2026a | `Allen_et_al._-_2026_-_Is_it_as_simple_as_run_more,_win_more_Influence_of_running_load_on_match_outcome_and_final_league_p` |
| Allen2026b | `Allen_et_al._-_2026_-_Possession_in_motion_a_five-season_analysis_of_running_in-possession_and_out-of-possession_with_mat` |
| Chen2025 | `Chen_et_al._-_2025_-_Establishing_reference_values_for_the_match_running_performances_of_thirteen_specific_positional_rol` |
| Morgans2025b | `Morgans_et_al._-_2025_-_The_positional_demands_of_explosive_actions_in_elite_soccer_Comparison_of_English_Premier_League_an` |
| Morgans2025c | `Morgans_et_al._-_2025_-_Comparison_of_running_and_accelerometry_variables_based_on_match_outcome,_match_location_and_quality` |
| Castellano2024 | `Castellano_et_al._-_2024_-_Tell_me_how_much_your_opponent_team_runs_and_I_will_tell_you_how_much_you_should_run_A_predictive_m` |
| Castellano2025 | `Castellano_et_al._-_2025_-_Match_physical_performance_profiles_in_professional_football_a_comparative_analysis_among_players’` |
| Deutsch2025 | `Deutsch_et_al._-_2025_-_Frequency_and_intensity_of_change_of_directions_in_German_Bundesliga_soccer` |
| VighLarsen2018 | `Vigh-Larsen_et_al._-_2018_-_Position-Specific_Acceleration_and_Deceleration_Profiles_in_Elite_Youth_and_Senior_Soccer_Players` |
| AlonsoCallejo2024 | `Alonso-Callejo_et_al._-_2024_-_Validity_and_Reliability_of_the_Acceleration-Speed_Profile_for_Assessing_Running_Kinematics'_Variabl` |
| Andrzejewski2022 | `Andrzejewski_et_al._-_2022_-_Analysis_of_team_success_based_on_match_technical_and_running_performance_in_a_professional_soccer_l` |
| Longo2021 | `Longo_et_al._-_2021_-_The_influence_of_athletic_performance_on_the_highest_positions_of_the_final_ranking_during_20172018` |
| Skiba2021 | `Skiba_and_Clarke_-_2021_-_The_W′_Balance_Model_Mathematical_and_Methodological_Considerations` |
| Lievens2024 | `Lievens_et_al._-_2024_-_Characterizing_the_Exponential_Profile_of_W′_Recovery_Following_Partial_Depletion` |
| Chorley2022 | `Chorley_et_al._-_2022_-_Bi‐exponential_modelling_of_W_reconstitution_kinetics_in_trained_cyclists` |
| Chorley2023 | `Chorley_et_al._-_2023_-_A_dynamic_model_of_the_bi-exponential_reconstitution_and_expenditure_of_W′_in_trained_cyclists` |
| Bellenger2025 | `Bellenger_et_al._-_2025_-_Validation_of_End-of-Session_D′_Balance_for_Quantifying_and_Differentiating_Exhaustive_and_Nonexhaus` |
| Weigend2023 | `Weigend_et_al._-_2023_-_A_hydraulic_model_outperforms_work-balance_models_for_predicting_recovery_kinetics_from_intermittent` |
| Kavanagh2024 | `Kavanagh_et_al._-_2024_-_The_relationships_between_distances_covered_above_generic_and_relative_speed_thresholds_by_male_socc` |
| Morgans2025 | `Morgans_et_al._-_2025_-_Contextualized_high-speed_running_and_sprinting_during_English_Premier_League_match-play_with_refere` |
| Bortnik2022 | `Bortnik_et_al._-_2022_-_The_mean_and_peak_physical_demands_during_transitional_play_and_high_pressure_activities_in_elite_fo` |
| SilvaH2025 | `Silva_et_al._-_2025_-_Peak_match_sprinting_speed_during_soccer_matches_analysing_the_pre-_and_post-peak_speed_dynamics` |
| daSilva2025 | `da_Silva_et_al._-_2025_-_The_interplay_between_pitch_control_and_top_speed_in_soccer_considering_the_stamina_factor` |
| Bassek2025 | `Bassek_et_al._-_2025_-_An_integrated_dataset_of_spatiotemporal_and_event_data_in_elite_soccer` |
| Mohr2003 | `Mohr_et_al._-_2003_-_Match_performance_of_high-standard_soccer_players_with_special_reference_to_development_of_fatigue` |
| Mohr2005 | `Mohr_et_al._-_2005_-_Fatigue_in_soccer_A_brief_review` |
| Osgnach2010 | `Osgnach_et_al._-_2010_-_Energy_Cost_and_Metabolic_Power_in_Elite_Soccer` |
| diPrampero2005 | `Di_Prampero_et_al._-_2005_-_Sprint_running_a_new_energetic_approach` |
| Skiba2012 | `Skiba_et_al._-_2012_-_Modeling_the_Expenditure_and_Reconstitution_of_Work_Capacity_above_Critical_Power` |
| Jones2017 | `Jones_and_Vanhatalo_-_2017_-_The_‘Critical_Power’_Concept_Applications_to_Sports_Performance_with_a_Focus_on_Intermittent_High-I` |
| Spearman2017 | `Spearman_et_al._-_2017_-_Physics-Based_Modeling_of_Pass_Probabilities_in_Soccer` |
| Spearman2018 | `Spearman_-_2018_-_Beyond_Expected_Goals` |
| Fernandez2018 | `Fernandez_et_al._-_Wide_Open_Spaces_A_statistical_technique_for_measuring_space_creation_in_professional_soccer` |
| Narizuka2023 | `Narizuka_et_al._-_2023_-_Validation_of_a_motion_model_for_soccer_players’_sprint_by_means_of_tracking_data` |
| Ju2022 | `Ju_et_al._-_2022_-_Contextualised_peak_periods_of_play_in_English_Premier_League_matches` |
| Cortez2026 | `Cortez_et_al._-_2026_-_Physical,_tactical_and_technical_performance_of_the_most_demanding_passages_of_kinematic_activity_in` |
| Fang2024 | `Fang_et_al._-_2024_-_Physical_and_technical_performance_in_and_after_the_worst-case_scenario_in_matches_of_the_Chinese_Su` |
| Niu2026 | `Niu_et_al._-_2026_-_Intra-positional_technical_performance_under_different_physical_demands_in_elite_football_a_compari` |
| Dambroz2022 | `Dambroz_et_al._-_2022_-_The_effect_of_physical_fatigue_on_the_performance_of_soccer_players_A_systematic_review` |
| Wang2024 | `Wang_et_al._-_2024_-_A_Systematic_review_of_the_factors_that_affect_soccer_players’_short-passing_ability—based_on_the_Lo` |
| SilvaJR2018 | `Silva_et_al._-_2018_-_Acute_and_Residual_Soccer_Match-Related_Fatigue_A_Systematic_Review_and_Meta-analysis` |
| Rampinini2008 | `Rampinini_et_al._-_2008_-_Effect_of_Match-Related_Fatigue_on_Short-Passing_Ability_in_Young_Soccer_Players` |
| Russell2011 | `Russell_et_al._-_2011_-_The_Effects_of_Fatigue_on_Soccer_Skills_Performed_During_a_Soccer_Match_Simulation` |
| Carling2011 | `Carling_and_Dupont_-_2011_-_Are_declines_in_physical_performance_associated_with_a_reduction_in_skill-related_performance_during` |
| Krustrup2006 | `Krustrup_et_al._-_2006_-_Muscle_and_Blood_Metabolites_during_a_Soccer_Game` |
| Akenhead2013 | `Akenhead_et_al._-_2013_-_Diminutions_of_acceleration_and_deceleration_output_during_professional_football_match_play` |
| Thoseby2022 | `Thoseby_et_al._-_2022_-_Temporal_distribution_of_peak_running_demands_relative_to_match_minutes_in_elite_football` |
| Thoseby2023 | `Thoseby_et_al._-_2023_-_Positional_and_temporal_differences_in_peak_match_running_demands_of_elite_football` |
| Buchheit2015 | `Buchheit_et_al._-_2015_-_Monitoring_Locomotor_Load_in_Soccer_Is_Metabolic_Power,_Powerful` |
| Bradley2013 | `Bradley_and_Noakes_-_2013_-_Match_running_performance_fluctuations_in_elite_soccer_Indicative_of_fatigue,_pacing_or_situational` |
| Paul2015 | `Paul_et_al._-_2015_-_Factors_Affecting_Match_Running_Performance_of_Elite_Soccer_Players_Shedding_Some_Light_on_the_Comp` |
| Bangsbo2006 | `Bangsbo_et_al._-_2006_-_Physical_and_metabolic_demands_of_training_and_match-play_in_the_elite_football_player` |
| Hills2018 | `Hills_et_al._-_2018_-_Profiling_the_Responses_of_Soccer_Substitutes_A_Review_of_Current_Literature` |
| Sutcliffe2025 | `Sutcliffe_and_Kramer_-_2025_-_Exploring_the_utility_of_the_3-minute_all-out_running_test_in_assessing_match_performance_and_extern` |
| Modric2020 | `Modric_et_al._-_2020_-_Aerobic_fitness_and_game_performance_indicators_in_professional_football_players;_playing_position_s` |
| Slimani2019 | `Slimani_et_al._-_2019_-_Maximum_Oxygen_Uptake_of_Male_Soccer_Players_According_to_their_Competitive_Level,_Playing_Position` |
| Xu2026 | `Xu_et_al._-_2026_-_Comparative_effectiveness_of_training_interventions_on_VO2max_in_male_soccer_players_a_systematic_r` (Markdown only) |
| Liu2021 | `Liu_et_al._-_2021_-_Comparing_critical_speed_modelling_approaches_and_exploring_relationships_with_match-play_variables` |
| MarquesJimenez2017 | `Marqués-Jiménez_et_al._-_Fatigue_and_Recovery_in_Soccer_Evidence_and_Challenges` (no year in the file name) |
| Snyder2023 | `Snyder_et_al._-_2023_-_Indicators_of_Fatigue_during_a_Soccer_Match_Simulation_Using_GPS-Derived_Workload_Values_Which_Metr` |
| Smith2018 | *not downloaded* |
| Julian2021 | *not downloaded* |
| Bradley2009 | `Bradley_et_al._-_2009_-_High-intensity_running_in_English_FA_Premier_League_soccer_matches` |
| DiSalvo2007 | `Di_Salvo_et_al._-_2007_-_Performance_Characteristics_According_to_Playing_Position_in_Elite_Soccer` |

`Snyder_et_al._-_2023_…` and `Marqués-Jiménez_et_al._…` are outside the source rule (section F); use only as described there.
