# Developments

All numbers approximate

* Hungerford
  * approx 60 detached added in 2021-2023 - Jethro Tull way
  * approx 15 terraced houses added around the church - Lourdes Crescent - church project?
* Reading
  * Constantly adding new flats across the town for the last 30 years
* Thatcham
  * No new general residential development since 2020!
  * 2020+ - approx 100 retirement flats added (e.g. Turner House, William House) near Waitrose
  * 2019-2020 - 45 houses on Sowerby St plus small flat developments in town
  * 2010-2016 - 6 year lull in development, adding a handful of new dwellings each year
  * 1995-2002 - 600 new builds on Dunstan Park - huge growth - heavy skew towards detached properties
  * 1998-2003 - approx 100 on pound lane/lower way near the sewage works
  * 2003-2008 - 500 new builds on Kennet Heath with a more equal mix of of property type
* Newbury
  * Much more flat development over the last 25 years - approx 2000 flats added in that time, notably:
    * Racecourse flats (~450)
    * Conversion of offices around Hambridge Lane (~100)
    * 200+ in the town centre, including above the Park Way shopping centre
  * 500 detached and 380 semi detached added in the same period, including
    * Sizeable new development in Greenham (~200 detached houses added out of ~350 homes)
    * Sandleford Lodge - (~70 of 200 homes added detached)

# More info

## Research methodology

This section is written from a data-driven planner's perspective. The aim is to derive housing need and the appropriate mix from first principles — demographics, affordability, the Land Registry transaction record, and the historical build pattern — rather than start from any pre-existing planning target. Sources are linked inline.

## Thesis (one-page summary)

After working the data carefully, I land in a more nuanced place than I started:

1. **West Berkshire as a whole needs more housing.** Affordability ratio ~10× (vs England 7.7×), real prices outrunning real wages for 25+ years, district under-delivery vs the standard-method requirement for most of the last decade. This is well-evidenced.

2. **There is *no* clean Thatcham-specific demand signal in the price or transaction data.** Thatcham's long-run real price growth tracks the national trend (+1.56%/yr vs England ~+1.3%/yr). Its premium relative to the West Berks median has bounced in a narrow band for 30 years (relative index 95–105). Its turnover is at the national average and the 2000s peak was new-build accounting, not demand. The within-type prices show Thatcham at *parity* with the district on terraced and within noise on flats and semis; the 20% gap on detached is a product story (older estate-built stock), not a demand story. None of this picks Thatcham out.

3. **The one thing that is genuinely Thatcham-specific is the 15-year delivery freeze.** Population +11.6% (2001–2021) on a dwelling stock that has barely moved since 2010. Every other West Berks settlement of similar size has continued to add stock through the same period. Thatcham has not.

4. **Therefore the case for putting a strategic allocation specifically in Thatcham rests on four things, none of which is "local demand pressure":**
   - **District apportionment** — the district needs the homes somewhere.
   - **Catch-up** — Thatcham's share of the district under-delivery is 600–1,000 homes by my pro-rata estimate.
   - **Siting fit (transport-led, not jobs-led).** Local employers (Vodafone, AWE) are stable-to-shrinking and have been here for decades, so the demand isn't *new local jobs*. But Thatcham has direct electrified rail to **Reading** — the regional employment cluster that *is* growing post-Elizabeth Line — plus the A4 / M4 J13 corridor. The siting case is "good transport to where the jobs are growing," not "the local jobs are growing."
   - **Regulatory path of least resistance.** This is the honest motivator that planning documents tend not to spell out. Most of the rest of West Berkshire is constrained: North Wessex Downs AONB (west and south), AWE DEPZ (east), Kennet & Lambourn floodplain (river corridors), greenbelt fragments, Newbury at infill saturation. Thatcham sits in a corridor that is *relatively* free of these designations, with most utilities, rail and road already in place. Allocations land here because they *can*, not because the data picks Thatcham out as the best location on positive grounds. This is the underlying mechanism that has made Thatcham the *dormitory* of West Berkshire — accumulating residential growth without a corresponding expansion of local employment, civic infrastructure or town-centre function. Each new allocation reinforces that pattern unless deliberately countered.

5. **What this means for "how many":** a defensible pro-rata + catch-up figure is **1,400–2,200 homes over 15 years**. Anything materially larger is not derivable from a Thatcham-specific need argument — it is a *capacity / siting / strategic* judgement (Thatcham should take more than its share because the alternatives are worse), which is legitimate but should be labelled honestly.

6. **What this means for "what type":** the affordability gap is at the entry-level price point, and Thatcham is *already* at district parity for terraced. So new build should weigh toward 2–3 bed terraced and small-semi for affordability/first-time-buyer reasons. The detached 20% gap is a product issue, not a demand shortage. Continued retirement-flat dominance (every Thatcham new-build sale since 2022 has been a flat) does not match the underlying mix demand.

The rest of this document walks through the evidence in detail.

## 1. What the Price Paid data shows (2001–2025)

Source: `temp/Price Paid Analysis.html` from this repo (Land Registry PPD, OS Open UPRN, ONS CPI). Excludes property type O and the latest year (registration lag).

### Address stock (UPRN count, polygon-defined)

| Area | Addresses | Sales 2001-2025 | Approx turnover (sales/yr ÷ stock) |
|------|-----------|------------------|-------------------------------------|
| Newbury polygon  | 25,106 | 20,936 | 3.34% |
| Thatcham polygon | 12,250 | 12,232 | 3.99% |
| West Berkshire   | ~101,882 | ~64,000 | ~2.5% (excl. urban-dense towns) |

**Read:** Thatcham's transaction rate has been **20% higher than Newbury's** and well above the rural-heavy West Berkshire average. But before drawing a "high demand" conclusion from this, see the turnover caveat below — most of the elevation in the Thatcham series comes from new-build sales being counted during the 2000s build-out, not from elevated resale churn.

### Median prices, real growth and premium vs district

| Area | 1995 median | 2025 median | Nominal growth | Real CAGR (CPI-deflated) | Premium vs W. Berks 2025 |
|------|-------------|-------------|----------------|---------------------------|---------------------------|
| Newbury  | £65,000 | £350,000 | +438% | +1.62%/yr | 87% (13% below) |
| Thatcham | £65,000 | £360,000 | +454% | +1.56%/yr | 90% (10% below) |
| West Berks | £74,000 | £400,500 | +441% | — | 100% |

**Read with caution:** Both towns have grown at almost the same rate in real terms. Thatcham's 2025 median (£360k) just sat above Newbury's (£350k), and the Thatcham-vs-district premium has nudged from 84.7% (2020) to 89.9% (2025). But the year-to-year bounce in the premium series is large — between 2015 and 2025 Thatcham has been above Newbury in **4 of 11 years** and the long-run averages (Newbury 91%, Thatcham 87%, a ~4pp gap) are barely outside the noise band. With ~350–500 Thatcham sales per year, single high-value detached transactions can shift the annual median by ±£10k. The honest read is therefore "the historic discount has narrowed, not disappeared" — not "Thatcham has overtaken Newbury". I have de-weighted this signal in the conclusions below.

### Property mix (% of all sales)

Thatcham (averaged 2020–2025):
- Detached **24%** · Semi-detached **36%** · Terraced **25%** · Flat **15%**

Newbury (averaged 2020–2025):
- Detached **19%** · Semi-detached **23%** · Terraced **24%** · Flat **34%**

**Read:** Thatcham's market is overwhelmingly family-housing (~85% houses). Newbury's market is now roughly **1-in-3 flats**, by far the highest share in West Berkshire — a direct consequence of two decades of [Newbury Racecourse](https://newburyracecourse.co.uk/redevelopment/david-wilson-homes/) (~1,500 dwellings, with the heavy flat content delivered first), Park Way town-centre flats, and the Hambridge Lane office-to-resi conversions.

### New-build delivery, by year

Thatcham new-build sales, summed by completed window (PPD lags completion by 6-8 weeks, so this is a faithful proxy for delivery):

| Window | New-build sales | Dominant mix | Tied to |
|--------|----------------|---------------|---------|
| 2001-2003 | ~270 | Detached + flat | Tail of Dunstan Park, Lower Way infill |
| 2004-2008 | ~613 | Mixed (~30% det / 25% sd / 25% terr / 20% flat) | **Kennet Heath** (Persimmon / Redrow / Wilson) |
| 2009-2016 | ~95 (≈12/yr) | Very thin | Sowerby St, scattered windfalls |
| 2017-2020 | ~173 | Heavy in flats (Turner / William House retirement) | Town-centre retirement / care |
| 2021-2025 | ~92 | **100% flats since 2022** | Final retirement-flat blocks; zero houses |

Newbury new-build sales, same windows:

| Window | New-build sales | Notable pattern |
|--------|----------------|------------------|
| 2001-2007 | ~1,485 | High volume — Greenham regeneration, town-centre flats |
| 2008-2012 | ~263 | Post-GFC collapse, **still 60–80% flats** |
| 2013-2018 | ~993 | Racecourse Phase 1 — peak flat delivery (2015: 163 flats vs 18 detached) |
| 2019-2025 | ~500 | Racecourse tail-out, mix re-balancing, but still flat-dominated |

**Key insight:** since **2010** Thatcham has effectively delivered no new family housing. From 2024 onward, new-build sales of detached, semi-detached and terraced houses in the polygon are **literally zero**. Every new-build sale recorded in the past two years has been a flat — and almost all of those are over-55 retirement units. This is the strongest single signal in the dataset.

### Turnover & liquidity — what it does and doesn't tell us

National turnover averaged 3.4% since 2015. Thatcham averages 3.4% in the same period; Newbury 3.2%. Historic peaks:

- Thatcham hit **6.0%+** turnover in 1999–2007 (six consecutive years).
- The peak coincided exactly with Dunstan Park tail and Kennet Heath build-out.
- Post-2010, Thatcham turnover stabilises at the national average.

**Careful with this one — turnover is largely a counting artefact of new build, plus normal life-cycle churn.** Every completion produces a first sale that lands in the numerator. Strip out the new-build sales and the 2000s peak shrinks substantially:

| Year | Total sales | New-build | Resales | Resale turnover |
|------|-------------|-----------|---------|-----------------|
| 2004 | 775 | 192 | 583 | 4.8% |
| 2007 | 695 | 103 | 592 | 4.8% |
| 2015 | 467 | 12  | 455 | 3.7% |

The new-build inflow was adding ~1–1.5 pp to Thatcham's apparent "demand" throughout the boom. The 2000s weren't a period of unusually high resale churn — they were a period of high *delivery*, which mechanically inflates turnover.

This means **turnover should not be read as a supply-and-demand signal at all**. It is mostly a churn rate (how often households move for life-cycle reasons). Houses always sell everywhere; the floor on turnover in any functioning UK market is set by job moves, family change, downsizing and death — not by stock shortage. Two towns with identical turnover can have very different levels of unmet need.

**Prices vs incomes is a better signal than turnover — but with a big caveat about what it actually proves.**

- Real CAGR for Thatcham 2001–2025: **+1.56%/yr**.
- England median real CAGR 2001–2024: **~+1.3%/yr** (England median £121k → £290k, CPI +85%).
- Thatcham relative-to-West-Berkshire index, 2025: **102.3** (essentially flat after 30 years). In 2010 it was 94.7, so the 2020s rise is reversion, not breakout.
- Affordability ratio: rose from ~5× in 1999 to ~10× in 2024 (ONS) — but England's ratio rose from ~4× to ~7.7× over the same period. **The doubling is a national feature, not a Thatcham one.**

**This is important — and walks back a claim I made earlier.** Real house prices outrunning real wages is a *nationwide* pattern since the late 1990s, driven by interest-rate compression, mortgage-lending evolution, planning constraints generally, and demographic / international-capital factors. It is not Thatcham-specific evidence of local supply pressure. Thatcham has essentially tracked the national/regional trend; over 30 years it has out-grown the West Berkshire average by ~2pp, which is within noise.

So the honest read is: **the price data tells me Thatcham is plumbed into the same regional housing market as the rest of the South East, and that market has had a multi-decade structural imbalance.** It does *not* tell me Thatcham specifically is under more pressure than its neighbours. Within-type figures reinforce this — terraced is at parity, semi 13% below, detached 20% below; none of these spreads have been widening dramatically.

In short:
- Turnover tells me the market is *functioning normally* (life-cycle churn + new-build accounting).
- Long-run prices tell me the *national / regional* market has had persistent supply shortage.
- Neither tells me Thatcham specifically has more unmet demand than other West Berks settlements.

That meaningfully weakens any argument of the form "Thatcham must take a disproportionate share *because the data shows it's especially stressed*". It doesn't show that. What it does support is: West Berkshire as a whole needs more supply (the affordability ratio is too high for the region), and the *where* question has to be settled on other grounds — physical capacity, infrastructure, jobs and transport (§2). That's where Thatcham's specific case has to be built.

### Price by property type (2025)

| Type | Newbury median | Thatcham median | Ratio to flat |
|------|----------------|------------------|----------------|
| Detached | £591,250 | ~£540,000 | 2.5–2.8× |
| Semi-detached | £410,250 | ~£395,000 | 1.9× |
| Terraced | £345,000 | ~£330,000 | 1.6× |
| Flat | £215,000 | ~£215,000 | 1.0× |

The 2.8× gap between flat and detached in Newbury is the largest in the series and means that any further skew toward detached new build will widen — not narrow — the affordability gap for entry-level buyers.

### Within-type comparison vs the district (2025 medians, Land Registry)

The 10% headline discount to the district median hides a very uneven picture once you split by type:

| Type | Thatcham | Newbury | W. Berks | Thatcham vs W. Berks |
|------|----------|---------|----------|----------------------|
| Detached | £505,000 (85 sales) | £591,250 (130) | £630,000 (657) | **−20%** |
| Semi-detached | £353,750 (142) | £410,250 (150) | £405,000 (658) | −13% |
| Terraced | £330,000 (97) | £345,000 (160) | £336,500 (472) | **−2%** (par) |
| Flat | £190,250 (36) | £215,000 (226) | £215,000 (352) | −12% |

**This matters a lot and is its own story.** Thatcham is *at parity* with the district on terraced housing and only ~12–13% off on semi-detached and flat — but **detached is 20% below**. The "Thatcham is 10% below the district" headline is a mix-weighted average; on a like-for-like basis, the only segment where Thatcham trades at a substantial discount is the top of the market.

Why? Two plausible reasons, neither flattering to a "build more detached" strategy:

1. **Product, not location.** Thatcham's detached stock is overwhelmingly 3–4 bed estate-built family houses from Dunstan Park (1990s) and Kennet Heath (2000s). The W. Berks district average is pulled up by 4–5 bed prestige homes in the AONB villages (Hermitage, Cold Ash, Compton, Pangbourne) and along the river corridor. The gap reflects the product on the ground, not buyer demand for Thatcham.

2. **Lower revenue per plot for any new detached scheme.** A new detached unit on a Thatcham edge site will clear at ~£500–550k, not the ~£700k+ that a rural W. Berks village would achieve. That has direct implications for a developer's pro-forma — affordable-housing percentages, S106 / CIL contributions and infrastructure capacity have to be sized to Thatcham economics, not district-wide averages. **The council's negotiating leverage on affordable provision is structurally weaker on a Thatcham site than on, say, Sandleford** for this reason.

Two takeaways for the mix question:
- The unmet **affordability** need sits at the terraced / small-semi end where Thatcham is already at district parity — i.e. the entry-level price point is *not* artificially cheap in Thatcham, it's tracking the district. Building more of this segment is what closes the affordability gap for first-time buyers and key workers.
- More detached in Thatcham *would* find buyers (85 sales/yr already clear at £505k median), and there is arguably a quality-uplift case — modern 4-bed detached could pull Thatcham's detached median closer to the district. But that is a market-shaping argument, not a need-based one, and the developer-economics constraint above limits how aggressive the council can be on affordable contributions if the mix tilts that way.

## 2. Demographic and affordability context

### Population (Census)

- West Berkshire 2011: ~153,800; 2021: 161,400 (+5.0%) — ONS [Census 2021](https://www.ons.gov.uk/visualisations/censuspopulationchange/E06000037/). Slower than the South East (+7.5%) and England (+6.6%).
- Thatcham parish 2001: 22,824; 2021: 25,464 (+11.6% over 20 years, ~132/yr).
- Thatcham has grown faster than the district despite contributing **almost no new general dwellings** since 2010 — i.e. growth is happening by household densification, internal migration and natural change in the existing stock.

### Households

- West Berkshire 2021: 66,658 households ([ONS Census 2021](https://www.ons.gov.uk/visualisations/censusareachanges/E06000037/)).
- 27% are single-person households (a key driver of new dwelling need: more households per head of population).
- Owner-occupancy fell 69.7% → 67.6% between 2011 and 2021; private rented sector rose by 3.4 pp (faster than the regional average). The shift to renting in a high-value market is a textbook indicator of affordability stress.

### Affordability

- ONS [Housing affordability in England and Wales 2024](https://www.ons.gov.uk/peoplepopulationandcommunity/housing/bulletins/housingaffordabilityinenglandandwales/2024): England median price ÷ median earnings = **7.7×**.
- Berkshire-wide local-authority range = 8.3× (Reading) to 11× (Windsor & Maidenhead) per the [House of Commons Library briefing](https://commonslibrary.parliament.uk/research-briefings/SN01922/).
- West Berkshire sits inside this range. A 2025 median price of £400,500 against median full-time resident earnings of ~£40k implies a ratio of **~10×** — i.e. about 1.3× the England average. Anything above ~5× is conventionally regarded as "seriously unaffordable" (Demographia threshold).
- ONS [West Berkshire housing prices](https://www.ons.gov.uk/visualisations/housingpriceslocal/E06000037/) (Feb 2026): average price £403k, first-time-buyer average £316k. Average monthly rent £1,273 (+2.6% YoY).

### Jobs and transport — the demand-side drivers

This deserves a section of its own. A planner judging *where* in West Berkshire to allocate housing has to look at the labour market the new residents will plug into and the transport that gets them there.

**Honest read on local employers — they are stable, not growing.** I initially overstated this. A closer look at the evidence:

| Employer | Approx jobs at site | Distance from Thatcham | Recent direction |
|----------|---------------------|------------------------|------------------|
| Vodafone UK HQ (Newbury) | **~4,128** at Newbury campus ([Mobilityways](https://www.mobilityways.com/vodafone/)) | ~3 mi west | **Likely contracting.** Announced 11,000 global redundancies over 3 yrs from May 2023 ([Berkshire Live](https://www.getreading.co.uk/news/reading-berkshire-news/newbury-staff-face-cuts-vodafone-26930223)). The widely-cited "+600 net gain to Newbury" is a 2019 relocation from Bracknell ([Newbury Today](https://www.newburytoday.co.uk/news/10m-investment-and-staffing-restructure-for-newburys-vodafone-hq-9185350/)) — UK-internal shuffle, not net new jobs to the South East. |
| "The Connection" (former Vodafone HQ, 38 acres) | Contingent | ~3 mi west | Oval Real Estate redeveloping as innovation/life-sciences campus ([Costar](https://www.costar.com/article/362906113/oval-kicks-off-massive-makeover-of-former-berkshire-vodafone-campus-space)). Speculative new occupiers, no committed headcount yet. |
| AWE Aldermaston / Burghfield | **~9,500** combined; ~6,000 at Aldermaston | 8–12 mi east | **Stable.** 400–500 redundancies 2024–25 with MOD stating headcount maintained by replacement hire ([Newbury Today](https://www.newburytoday.co.uk/news/job-losses-could-be-replaced-with-different-roles-at-awe-say-9442208/)). Capital programme (new build campus) but flat workforce. |
| Bayer UK HQ (Reading) / Stryker / National Instruments / Newbury BS | Several thousand combined | 3–15 mi | No published growth/shrinkage signal; assume stable. |

**Two reframings the data forces on me:**

1. **The Newbury / West Berkshire local labour market is mature and stable, not expanding.** Both anchor employers (Vodafone, AWE) have been at their current sites for 20+ years and are currently *restructuring or contracting*, not growing. Housing demand from these employers is therefore *replacement/churn* demand (people retire, change jobs, move) — substantial and steady, but not increasing. The case for new housing in this area is **not** "more jobs are coming, we need more homes."

2. **The real *growing* labour market is Reading, not West Berkshire.** Reading borough has ~120k jobs in financial services and tech, has visibly grown post-Elizabeth Line (house prices +33% since 2014 vs +22% regional average; rents +25% in a year), and is now the regional employment gateway. The case for Thatcham as a housing site therefore rests *not* on local employer growth but on the fact that **Thatcham has direct electrified rail to a growing employment cluster** at Reading — and through it, Crossrail-connected access to central London / Canary Wharf.

The district's overall West Berkshire BRES figure shows +10.8% employees 2021→22, but that's COVID rebound, not sustained growth — BRES is explicitly cautioned against time-series use ([ONS BRES](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/datasets/localauthoritydistrictbusinessregisterandemploymentsurveybrestable6)). I don't have a clean trend figure to cite.

**Transport position:**

- **Thatcham railway station** — on the GWR Reading–Newbury–Bedwyn line; electrified in 2018; runs Class 800/387 stock. Passenger entries+exits **0.465 million in 2024/25**, recovering from 0.107m in 2020/21 ([Wikipedia](https://en.wikipedia.org/wiki/Thatcham_railway_station)). That's the steepest post-COVID rebound of any local station and signals real, sustained commuter use.
- **Journey time to Reading** ~12–15 min by train, then Elizabeth Line to Canary Wharf/Liverpool Street, or fast GWR to Paddington (~25 min). End-to-end Thatcham → central London is ~55–70 min — competitive with much of outer London by car or commuter rail.
- The **Elizabeth Line "effect"** is now established in the data: Reading house prices +33% since opening vs +22% South-East regional average; rents +25% ([Chancellors](https://www.chancellors.co.uk/news/property-news/research/house-prices-in-commuter-towns-benefit-from-crossrail)). Reading-radius towns with their own direct connection — Thatcham, Newbury — are next-order beneficiaries because they can absorb buyers priced out of Reading proper.
- **A4** runs through Thatcham; **M4 Junction 13** at Chieveley is 3 mi north; **A34** trunk route to Oxford/Southampton at Junction 13 also.
- AWE DEPZ (Detailed Emergency Planning Zone) constrains residential land *east* of the district but does not reach Thatcham itself — Thatcham is therefore one of relatively few sites where strategic-scale growth is *not* DEPZ-constrained.

**Planner read:** Thatcham is the best-connected town in West Berkshire after Newbury — arguably *as* well connected for the rail commuter, given that both share the same line. The jobs are clustered to the west (Vodafone / The Connection) and east (AWE / Reading) and Thatcham sits between them with direct rail and the A4. If new housing in West Berkshire is going to be matched to where the jobs and the trains are, Thatcham scores higher than most of the alternative sub-areas (Lambourn, Hungerford, Pangbourne, Compton, Kintbury) which lack one or both.

### The constraint map — why Thatcham keeps getting picked

There is a fourth driver, often unsaid in planning documents, that needs to be on the table: **Thatcham is the path of least planning resistance in West Berkshire.** It isn't necessarily the *best* place for growth on a positive-criteria assessment — it is, in many years, the *only easy* place. The constraint geography of the district forces allocations toward this corridor.

Going clockwise around the district:

- **North Wessex Downs AONB** covers a large swathe of the south and west of the district (Lambourn Downs, Berkshire Downs), making large-scale allocation in Hungerford, Lambourn, Compton, Kintbury, Hermitage and the rural-west settlements politically and legally very difficult.
- **AWE DEPZ** (Detailed Emergency Planning Zone) covers a 3 km radius around Aldermaston and Burghfield, ruling out substantial new residential growth in Tadley, Aldermaston, Mortimer, Burghfield Common, and constraining settlement extensions around that quadrant.
- **Kennet & Lambourn river floodplain** runs along the southern edges of both Newbury and Thatcham; the Inspector has already flagged it as a constraint on the indicative larger allocations and it limits the south side of either town.
- **Greenbelt fragments** in the east of the district (around Pangbourne / Theale / Tilehurst) and the SSSI / Site of Special Scientific Interest designations on heathland and chalk grassland further reduce candidate land.
- **Newbury itself** has reached high-density infill saturation (§4c) — new-build flats outsold new-build houses every year 2013–2018, and the easy town-centre / brownfield wins have already been delivered (Racecourse, Park Way, Hambridge Lane). Sandleford Park already absorbs the major southern edge expansion.

What's left when you exclude all of that? **Thatcham and its immediate hinterland** — flat-to-gently-rolling agricultural land north and north-east of the existing town, outside the AONB, outside the DEPZ, outside the floodplain (just), with rail and the A4 already in place. So allocations land here repeatedly, not because Thatcham has the strongest *case for* growth, but because everywhere else has a stronger *case against*.

This is **why Thatcham has become a dormitory of the county**. Over 30 years, the regulatory geography has steered consecutive waves of housing onto its northern edge (Dunstan Park 1990s, Kennet Heath 2000s, NE Thatcham proposals 2020s) without a matching expansion of employment, civic centre, secondary school capacity or social infrastructure. The town has grown to ~25,500 people without acquiring the centre of a town of that size — partly because each allocation arrived as estate-on-the-edge, configured for residents who would work in Newbury or Reading and sleep in Thatcham.

**Implications for any new allocation, honestly stated:**

1. The case for growth in Thatcham is partly a *negative* case — it's the easiest site to deliver, not necessarily the best.
2. That negative case is *legitimate* — the district has to house people somewhere, and the alternatives have stronger objections — but it should be named, not dressed up as a positive demand case.
3. **It also creates a planning obligation**: if Thatcham is asked to take another large allocation because the constraint map points there, the council has a duty to break the dormitory pattern this time — front-load civic infrastructure, employment land, secondary capacity, town-centre uplift — rather than repeat the estate-on-the-edge model. The historical precedents (Dunstan Park's lost school plot, Kennet Heath's lost rail bridge) are warnings of what happens when ease-of-approval is allowed to lower the bar on infrastructure.
4. There is also a *limit* to this argument. "Easy to approve" doesn't scale indefinitely — at some point the cumulative effect on flood risk, road capacity (A4 / A339), schools, GP capacity and town form crosses a threshold where Thatcham itself becomes the constraint. The data doesn't tell us where that threshold is, but it is closer now than it was in 1995.

## 3. Historical developments — reconstructed and dated

### Thatcham

| Development | Approx years | Approx homes | Notes / source |
|-------------|--------------|--------------|----------------|
| **Dunstan Park** (north Thatcham) | 1995–2002 | ~600 | Built late 1990s; documented infrastructure issues — flooding from culverted springs; primary-school plot reallocated to housing. See [WBC Strategic Growth Study Stage 1](https://www.westberks.gov.uk/media/49797/Thatcham-Strategic-Growth-Study-Stage-1-Thatcham-Past/pdf/Thatcham_Strategic_Growth_Study_Stage_1.pdf) |
| Pound Lane / Lower Way | 1998–2003 | ~100 | Edge-of-town near sewage works |
| **Kennet Heath** (south, near rail/A4) | 2004–2008 (residents from 2007) | 500–600 | Consortium build — Persimmon, Redrow, David Wilson. Redrow paid ~£1.5m for Station Road roundabout in lieu of promised rail bridge ([Newbury Today](https://www.newburytoday.co.uk/news/thatcham-bridge-will-it-ever-be-built-9387679/)); ongoing S38 highway-adoption disputes. [Resident site](http://www.kennetheath.co.uk/info/) |
| Sowerby St | 2019–2020 | ~45 | Small infill |
| Pound Lane Depot (Persimmon) | 2017–2020 | 47 (approved; 14 affordable) | [Newbury Today](https://www.newburytoday.co.uk/news/green-light-for-thatcham-depot-plans-9177387/). Application to raise to 61 was withdrawn ([NT](https://www.newburytoday.co.uk/news/plans-for-additional-thatcham-depot-homes-withdrawn-9185044/)) |
| Turner House / William House and similar over-55 blocks | 2020–2025 | ~100 retirement flats | Near Waitrose / town centre |

### Newbury

| Development | Approx years | Homes | Notes |
|-------------|--------------|-------|-------|
| **Newbury Racecourse** (Western, Central, Eastern parcels) | 2012 agreement, build 2013 → ongoing | up to 1,500 | DWH joint venture with the racecourse; 30% affordable / shared equity. First 421 homes launched 2013. [Construction Enquirer](https://www.constructionenquirer.com/2012/09/20/david-wilson-to-build-1500-new-homes-on-racecourse/), [Newbury Racecourse PLC announcement](https://newburyracecourse.co.uk/wp-content/uploads/2024/06/IR_190912-Newbury-Racecourse-PLC-Development-Agreement-with-David-Wilson-Homes.pdf) |
| Greenham regeneration (ex-airbase fringe) | early 2000s onward | ~350 of which ~200 detached | |
| Hambridge Lane office-to-resi | 2014–2018 | ~100 flats | Permitted Development conversions |
| Park Way town-centre flats | 2010s | ~200 | |
| **Sandleford Park (East — Bloor)** | Outline 2022; first reserved matters Apr 2025 | up to 1,080 | Granted at Section 78 appeal by SoS 2022. Includes 80-bed extra-care, 2FE primary, country park. Construction of spine road expected 2025/26. [LRM Planning summary](https://lrmplanning.com/project/sandleford-park/), [West Berks public access app 18/00764/OUTMAJ](https://publicaccess.westberks.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal=P693R4RD04Z00) |
| **Sandleford Park West (Donnington)** | Approved 2024–25 | up to 360 | First show homes summer 2025; 60 units/yr to 2032. [Newbury Today](https://www.newburytoday.co.uk/news/sandleford-west-360-homes-given-approval-by-west-berkshire-c-9363170/) |

### Other West Berkshire sites in the active pipeline

- ~225 NE Thatcham gap-filler (boundary land), 45 Henwick Park (Bowling Green Road), 25 north of Pangbourne Hill, 138 Pincents Lane Tilehurst — all identified as deliverable in the post-adoption five-year supply ([Newbury Today](https://www.newburytoday.co.uk/news/9-270-more-homes-a-year-for-west-berkshire-in-local-plan-rev-9393433/)).
- District five-year housing land supply: ~5.7 years against the post-2025 plan requirement ([WBC 5YHLS page](https://www.westberks.gov.uk/5yhls)).

## 4. Reading the trends — what the data is telling me

### 4a. The absence of a Thatcham-specific demand signal

This is worth being explicit about, because it is the central honest finding of the analysis: **the price-paid and transaction data do not provide any clean evidence that Thatcham specifically has more unmet demand than its West Berkshire neighbours.** If Thatcham were under exceptional local pressure, we would expect to see at least one of the following — and we don't see any of them:

| Signal you'd expect if Thatcham were uniquely demand-stressed | What the data actually shows |
|---|---|
| Real prices outgrowing district / national average | Thatcham real CAGR +1.56%/yr ≈ England real CAGR ~+1.3%/yr. Difference is within noise. |
| Affordability ratio worsening faster than the district | Thatcham tracks district which tracks region. The doubling from ~5× to ~10× is a national feature. |
| Premium vs district rising over time | Relative-to-district index: 100 (1995) → 94.7 (2010) → 102.3 (2025). Net 30-year movement: +2.3pp. Noise. |
| Within-type price gaps narrowing as buyers compete in | Terraced is *at parity* (-2%). Semi -13%, flat -12%, detached -20% — all roughly stable. The detached gap reflects older estate stock (product), not buyer scarcity. |
| Turnover elevated above the national rate | Thatcham resale-turnover ~national average since 2010. The historic peak (5–6% in 1999–2007) is a new-build counting artefact (§1). |
| New-build sales clearing at premium to resale comparable | New-build sales scarce since 2010 — but the retirement-flat blocks that did sell did not show a price-pressure premium relative to other regional retirement schemes. |

If any of those signals were present I would expect them to be visible against the noise floor over a 30-year series with 12,000+ Thatcham transactions. They are not. **The most candid read is that Thatcham is a normally-functioning sub-market of the regional housing system. It feels the same regional pressure as everywhere else in the South East. It is not under "extra" pressure.**

### 4b. What IS Thatcham-specific

Only one substantive thing, but it's real:

**Thatcham has effectively stopped building for ~15 years while its population has grown.** Population +11.6% between 2001 and 2021 on a dwelling stock that has added only ~150 net units (most of those retirement flats) since 2010. Every comparable West Berks settlement has continued to add stock through the same window — Newbury (Racecourse, Park Way, Hambridge Lane), Pangbourne, Hungerford (Jethro Tull Way), even small infill in the villages. Thatcham is the outlier in *delivery*, not in *demand*.

That under-delivery has been absorbed through:
- Densification of existing stock (more people per dwelling — particularly older households not downsizing, adult children at home for longer);
- Inward commuting from cheaper settlements further west;
- Outward displacement of would-be Thatcham movers into Newbury / Reading / further afield.

None of those mechanisms shows up as a "demand spike" in price-paid data, because none of them generate excess transactions or premiums — they are silent in the dataset.

### 4c. The district-level picture

| Trend | Local-specific? | What it tells us |
|---|---|---|
| Affordability ratio ~10× (district/regional) | No — national pattern | District-wide supply has not kept up with demand. Applies to Thatcham only because it applies everywhere. |
| Standard-method need ~1,070/yr; adopted plan 515/yr; delivery below either | District-level | Whatever the *correct* district number is, recent delivery has been short of it. |
| Newbury's flat-led model is saturated | Newbury-specific | New-build flats outsold houses 2013–2018; flat share now 34% of all sales — far above norm. Newbury cannot keep absorbing district growth at the current density. The next strategic site has to be somewhere else. |
| Mix in existing delivery is wrong for the demographic | District-level | 27% of W. Berks households are single-person but the flat supply already serves them; unmet demand is family housing 2–3 bed. Thatcham 2022–25 new-build mix is 100% flats — wrong for either Thatcham or the district. |
| Infrastructure has lagged past cycles | Local | Dunstan Park lost its school plot; Kennet Heath lost its rail bridge. Real and Thatcham-specific, but it is an *if-you-build* warning, not a *whether-to-build* argument. |

## 5. Independent planner conclusions

### Question 1 — Does Thatcham need a strategic-scale housing allocation?

To answer this I have to distinguish two questions that are easy to conflate:

> **(a) Is there evidence that *Thatcham specifically* has unmet local demand that justifies growth there for its own sake?**
> Answer: **No, not really.** §4a sets out the absence of evidence in detail. Thatcham real price growth, affordability ratio trajectory, relative-to-district premium, turnover and within-type price gaps all sit inside the regional/national pattern. The data does not pick Thatcham out.

> **(b) Does it make sense to put a substantial chunk of district-wide growth in Thatcham?**
> Answer: **Yes** — but it's a *siting* argument, not a *demand* argument.

The honest case for a strategic allocation in Thatcham rests on the following — and *only* the following:

1. **District-level housing need is real and undersupplied.** Affordability ratio ~10× against an England 7.7×; standard-method need ~1,070/yr; delivery short of that for the last decade. Those homes have to go somewhere.

2. **Thatcham under-delivered against its share for ~15 years.** The town's stock has barely moved since 2010 while population grew +11.6% over the wider window. Every other comparable West Berks settlement kept building. This is the one Thatcham-specific data finding (§4b) — and it is about *past delivery*, not about *current unmet demand*. The two are related (under-delivery creates pent-up household formation pressure regionally) but distinct.

3. **Siting fit — transport, not local jobs.** §2 sets out the rail / road position: electrified GWR line to Reading (the *growing* regional cluster post-Elizabeth Line), M4 J13, A4 corridor, station entries+exits 0.465m in 2024/25. The local employers (Vodafone, AWE) are stable-to-shrinking, not growing — so the case is "good transport access to a growing nearby employment cluster," not "the local labour market is expanding."

4. **Newbury infill saturation.** §4c — new-build flats outsold new-build houses in Newbury every year 2013–2018, flats are now 34% of sales, and 2023–2024 new-build family-house sales collapsed to single digits as Racecourse wound down. There is not much more high-density absorptive capacity in Newbury itself.

5. **Regulatory path of least resistance — the unsaid driver.** §2 ("The constraint map") sets this out. The North Wessex Downs AONB rules out the west and south, the AWE DEPZ rules out the east, the floodplain rules out the river corridors, and Newbury is at infill saturation. What's left is the Thatcham corridor. This is *why* Thatcham has become the dormitory of West Berkshire — it's where allocations land when everywhere else has a stronger objection. This is a legitimate motivator but it is a *negative* one (we can put it here) rather than a *positive* one (this is the best place for it), and it brings an obligation to break the dormitory pattern rather than entrench it further.

I am *explicitly not* arguing this from price signals (turnover, real growth, affordability trend, premium-to-district — see §4a). All of those reflect the *regional* housing market that Thatcham is part of, not a Thatcham-specific stress point.

**The framing matters because it disciplines the size question.** If Thatcham were itself under exceptional pressure, that would justify above-share allocation purely on local need. It isn't, so the case for a large allocation in Thatcham is a case for *taking more than the natural share of district growth*, justified by a mix of siting fit and regulatory ease. That is a legitimate planning argument but it is a different argument — and once it is honestly named, it raises a harder question: at what point does ease-of-approval stop being a sufficient reason and start being an excuse to entrench dormitory growth? (Q2 below.)

### Question 2 — How many, on a defensible derivation?

Two layered figures, each with a different evidential basis. They should not be conflated:

**Tier 1 — what *local* evidence supports (pro-rata + catch-up).** This is the number derivable from data that is genuinely Thatcham-specific.

- **Demographic pro-rata share.** WBC 2018-based household projections imply ~+5,000–7,000 households district-wide over 20 years. Thatcham at ~15–17% of district = **750–1,200 homes over 20 years**.
- **Catch-up for the 2010–2025 delivery freeze.** Natural Thatcham share ~50–75 homes/yr; actual ~10/yr → cumulative under-delivery **600–1,000 homes**.

**Combined Tier 1: ~1,400–2,200 homes over 15 years.** This is what the local evidence supports. It is roughly the scale of the 1995–2008 build-out in the same town (Dunstan Park + Kennet Heath + Pound Lane ≈ ~1,200 homes).

**Tier 2 — any number above Tier 1 is a siting/strategic judgement, not a needs derivation.** If the district choice is "put more here than Thatcham's natural share because the alternatives are worse" (Newbury saturated, AONB blocks western sites, DEPZ blocks eastern sites, rural villages lack infrastructure), that is *defensible* — see §2 jobs/transport — but it must be presented as a *strategic allocation* decision, not as a response to Thatcham being uniquely demand-stressed.

The data does not support framing any number above ~2,200 as "local need". Above that line, the honest description is: "we are choosing to concentrate district growth here for siting reasons, and the council is asking Thatcham to absorb a larger share than its proportionate one." That is a planning judgement, not a data finding.

### Question 3 — What type of homes?

This is where the data is most clear. The mix should *not* mirror what's recently been built. Recommended mix for a new strategic allocation in Thatcham, with reasoning:

| Type | Recommended share | Reasoning |
|------|-------------------|-----------|
| **2–3 bed terraced & small semi** | **40–45%** | Largest affordability gap; matches Thatcham's existing family-housing character (~25% terraced today). Entry-level for FTBs and downsizers. |
| **3–4 bed semi-detached** | **25–30%** | Thatcham's historic strength (36% of stock). Mid-market move-up housing chronically undersupplied since 2010. |
| **4–5 bed detached** | **10–15%** | Already 24% of resale stock; market is well-served and prices have outpaced incomes. Keep limited to avoid widening the affordability gap further. |
| **Flats / apartments** | **10–15%** *of which most should be affordable / shared ownership* | Market-rate flat supply is saturated in the local sub-market by Newbury's pipeline. Justified only as social rent, shared ownership, or specialist (younger single-person, key-worker) tenure. |
| **Specialist over-55 / care** | **5–10%** | Thatcham has already absorbed a wave of retirement flats 2020-25. Continued provision needed (demographic ageing) but at a measured pace. |

Tenure overlay: at minimum **30% affordable** (the standard W. Berks policy and the Racecourse precedent), heavily weighted toward social rent rather than shared ownership, to address the housing-register backlog. The Sandleford Park "extra care" component (80 beds within affordable) is a good template.

### Question 4 — Where, in light of constraints?

Thatcham faces real physical constraints any allocation has to plan around:
- **Flood risk** on the southern fringe along the Kennet & Lambourn floodplain (cited by the Planning Inspector as a constraint on Newbury 1,883 + Thatcham 2,855 envisaged allocations).
- **Air quality** on the A4 corridor and A339.
- **AONB** to the south (North Wessex Downs).
- **AWE DEPZ** to the east — a hard constraint.
- **Single secondary school** (Kennet) and a primary network with documented under-provision from past developments.

The geography of available land therefore pushes any large allocation to the **north/north-east** of the town, away from floodplain and AONB. Any scheme of this scale must front-load:
- a new primary school (not a re-allocated plot);
- secondary-school expansion or replacement, or a new 2FE feeder;
- a proper crossing of the rail line (the Kennet Heath promise the council let slip);
- SuDS designed for the catchment of culverted springs that flooded Dunstan Park;
- bus priority on the A4 + cycle network to Newbury / station.

## 6. Headline numbers (planner's summary)

- **Stock today (Thatcham polygon):** 12,250 addresses, ~25,500 people, ~85% houses / 15% flats.
- **Effective build rate 2010–2025:** ~10 homes/yr net, majority over-55 specialist flats.
- **Implied pro-rata build rate (Thatcham share of district household growth):** 50–75/yr.
- **Cumulative under-delivery 2010–2025:** ~600–1,000 homes (Thatcham-specific finding).
- **Tier 1 — defensible from local evidence:** **1,400–2,200 homes over 15 years** (pro-rata + catch-up). This is the number the data actually supports.
- **Tier 2 — anything above 2,200:** not a needs-based number; it is a *district siting / strategic concentration* judgement, defensible on jobs/transport/alternatives grounds (§2) but should be honestly labelled as such.
- **Mix:** 60–70% should be 2–3 / 3–4 bed houses (terraced + semi-detached); 30%+ affordable, weighted to social rent.
- **Largest single risk in repeating past mistakes:** mix-by-default (too many flats or too many detached), under-built social infrastructure, and ignoring the rail-bridge / floodplain / school precedents from Dunstan Park and Kennet Heath.

**One sentence summary:** the district needs more housing; the price data doesn't pick out Thatcham specifically; the case for putting it in Thatcham rests on transport access to Reading's growing employment cluster, the under-delivery in Thatcham since 2010, and — most importantly and least often said aloud — the fact that constraint geography (AONB, DEPZ, floodplain, Newbury saturation) makes Thatcham the path of least resistance for the district's growth, which is also why it has become the dormitory of West Berkshire.

## 7. Source list

- Land Registry Price Paid Data, OS Open UPRN, ONS CPI — analysed via this repo (`temp/Price Paid Analysis.html`).
- ONS [Census 2021 — How the population changed in West Berkshire](https://www.ons.gov.uk/visualisations/censuspopulationchange/E06000037/).
- ONS [Census 2021 — How life has changed in West Berkshire](https://www.ons.gov.uk/visualisations/censusareachanges/E06000037/).
- ONS [Housing prices in West Berkshire](https://www.ons.gov.uk/visualisations/housingpriceslocal/E06000037/) (Feb 2026 release).
- ONS [Housing affordability in England and Wales: 2024](https://www.ons.gov.uk/peoplepopulationandcommunity/housing/bulletins/housingaffordabilityinenglandandwales/2024).
- House of Commons Library [Regional house prices: affordability and income ratios SN01922](https://commonslibrary.parliament.uk/research-briefings/SN01922/).
- West Berkshire Council [Five-year housing land supply page](https://www.westberks.gov.uk/5yhls).
- West Berkshire Council [Thatcham Strategic Growth Study — Stage 1 (Thatcham Past)](https://www.westberks.gov.uk/media/49797/Thatcham-Strategic-Growth-Study-Stage-1-Thatcham-Past/pdf/Thatcham_Strategic_Growth_Study_Stage_1.pdf).
- Newbury Racecourse plc [Development Agreement with DWH (2012)](https://newburyracecourse.co.uk/wp-content/uploads/2024/06/IR_190912-Newbury-Racecourse-PLC-Development-Agreement-with-David-Wilson-Homes.pdf).
- Construction Enquirer [David Wilson to start 1500 new homes on racecourse](https://www.constructionenquirer.com/2012/09/20/david-wilson-to-build-1500-new-homes-on-racecourse/).
- LRM Planning [Sandleford Park summary](https://lrmplanning.com/project/sandleford-park/).
- West Berkshire Public Access [18/00764/OUTMAJ Sandleford outline](https://publicaccess.westberks.gov.uk/online-applications/applicationDetails.do?activeTab=summary&keyVal=P693R4RD04Z00).
- Newbury Today [Sandleford West approved (360 homes)](https://www.newburytoday.co.uk/news/sandleford-west-360-homes-given-approval-by-west-berkshire-c-9363170/).
- Newbury Today [Thatcham Bridge — Kennet Heath promise](https://www.newburytoday.co.uk/news/thatcham-bridge-will-it-ever-be-built-9387679/).
- Newbury Today [Pound Lane depot — green light](https://www.newburytoday.co.uk/news/green-light-for-thatcham-depot-plans-9177387/) and [withdrawal of extra homes](https://www.newburytoday.co.uk/news/plans-for-additional-thatcham-depot-homes-withdrawn-9185044/).
- Newbury Today [9,270 homes / Local Plan Inspector context](https://www.newburytoday.co.uk/news/9-270-more-homes-a-year-for-west-berkshire-in-local-plan-rev-9393433/) — used for pipeline reference only; the per-town target figures within that article were deliberately *not* used as anchors for the conclusions above.
- Kennet Heath [residents' information page](http://www.kennetheath.co.uk/info/).
- Newbury Today [AWE job changes 2024](https://www.newburytoday.co.uk/news/job-losses-could-be-replaced-with-different-roles-at-awe-say-9442208/).
