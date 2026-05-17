"""Pure-Python market summary calculations  -  no Streamlit imports."""

import statistics

from queries.price_paid_queries import real_stats_from_prices


def _safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _filtered_stats(stats_rows, latest_year, from_year=None, to_year=None):
    return [
        r for r in stats_rows
        if r["year"] != latest_year
        and (from_year is None or r["year"] >= from_year)
        and (to_year   is None or r["year"] <= to_year)
    ]


def price_growth_cagr(stats_rows, latest_year, from_year=None, to_year=None):
    """CAGR of median price from first to last year in range.

    Returns (cagr_pct, from_year, to_year) or None.
    """
    rows  = _filtered_stats(stats_rows, latest_year, from_year, to_year)
    years = sorted(r["year"] for r in rows)
    if len(years) < 2:
        return None
    by_yr  = {r["year"]: r for r in rows}
    y0, yn = years[0], years[-1]
    v0 = _safe_float(by_yr[y0]["median_price"])
    vn = _safe_float(by_yr[yn]["median_price"])
    n  = int(yn) - int(y0)
    if not (v0 and vn and n > 0):
        return None
    return ((vn / v0) ** (1 / n) - 1) * 100, y0, yn


def price_volatility(stats_rows, latest_year, from_year=None, to_year=None):
    """Coefficient of variation (%) of annual median prices. None if < 3 years."""
    rows    = _filtered_stats(stats_rows, latest_year, from_year, to_year)
    medians = [_safe_float(r["median_price"]) for r in rows if _safe_float(r["median_price"])]
    if len(medians) < 3:
        return None
    return (statistics.stdev(medians) / statistics.mean(medians)) * 100


def annual_turnover_rate(stats_rows, uprn_count, latest_year, from_year=None, to_year=None):
    """Mean annual sales as % of address stock. Returns (rate_pct, uprn_count) or None."""
    if not uprn_count:
        return None
    rows   = _filtered_stats(stats_rows, latest_year, from_year, to_year)
    counts = [int(r["count"]) for r in rows if r.get("count")]
    if not counts:
        return None
    return statistics.mean(counts) / uprn_count * 100, uprn_count


def average_new_build_share(mix_rows, latest_year, from_year=None, to_year=None):
    """Mean annual % of sales that are new builds."""
    mix = _filtered_stats(mix_rows, latest_year, from_year, to_year)
    if not mix:
        return None
    totals  = {}
    new_cnt = {}
    for r in mix:
        y = r["year"]
        totals[y]  = totals.get(y, 0) + r["count"]
        if r.get("old_new") == "Y":
            new_cnt[y] = new_cnt.get(y, 0) + r["count"]
    pcts = [new_cnt.get(y, 0) / t * 100 for y, t in totals.items() if t > 0]
    return statistics.mean(pcts) if pcts else None


def average_premium_vs_baseline(stats_rows, comparison_by_year, latest_year, from_year=None, to_year=None):
    """Mean ratio of polygon median to comparison baseline median (%). None if no overlap."""
    rows   = _filtered_stats(stats_rows, latest_year, from_year, to_year)
    ratios = []
    for r in rows:
        cmp = comparison_by_year.get(r["year"])
        pm  = _safe_float(r["median_price"])
        cm  = _safe_float(cmp["median_price"]) if cmp else None
        if pm and cm:
            ratios.append(pm / cm * 100)
    return statistics.mean(ratios) if ratios else None


def rank_polygons(summaries, key, higher_is_better=True):
    """Return {name: rank} dict, 1 = best. Missing keys omitted."""
    eligible = sorted(
        [(s[key], s["name"]) for s in summaries if key in s],
        reverse=higher_is_better,
    )
    return {name: i + 1 for i, (_, name) in enumerate(eligible)}


def build_cross_polygon_narrative(summaries):
    """Comparative sentences across polygons. Returns list of markdown strings."""
    sentences = []
    if len(summaries) < 2:
        return sentences

    def best(key, higher_is_better=True):
        eligible = [s for s in summaries if key in s]
        if len(eligible) < 2:
            return None, None, None, None
        ranked = sorted(eligible, key=lambda s: s[key], reverse=higher_is_better)
        return ranked[0]["name"], ranked[0][key], ranked[-1]["name"], ranked[-1][key]

    r = best("cagr")
    if r[0]:
        top_name, top_val, bot_name, bot_val = r
        gap = top_val - bot_val
        if gap >= 0.5:
            sentences.append(
                f"**Price growth**: {top_name} had the highest growth at **{top_val:+.1f}%/yr**, "
                f"{bot_name} the lowest at **{bot_val:+.1f}%/yr**  -  a spread of {gap:.1f} percentage points."
            )
        else:
            sentences.append(
                f"**Price growth**: all areas grew at a similar rate (~{top_val:+.1f}%/yr), "
                f"suggesting the markets move in lockstep."
            )

    r = best("volatility", higher_is_better=False)
    if r[0]:
        stable_name, stable_val, unstable_name, unstable_val = r
        spread = unstable_val - stable_val
        if spread >= 2:
            sentences.append(
                f"**Price stability**: {stable_name} was the most stable market (CV {stable_val:.1f}%), "
                f"{unstable_name} the most volatile (CV {unstable_val:.1f}%)  -  "
                f"{'a modest' if spread < 5 else 'a notable'} difference."
            )
        else:
            sentences.append(
                f"**Price stability**: similar volatility across all areas (CV {stable_val:.1f}%–{unstable_val:.1f}%)."
            )

    r = best("turnover")
    if r[0]:
        high_name, high_val, low_name, low_val = r
        spread = high_val - low_val
        if spread >= 0.3:
            ratio      = high_val / low_val if low_val else None
            ratio_note = f" ({ratio:.1f}× higher)" if ratio else ""
            sentences.append(
                f"**Liquidity**: {high_name} had higher annual turnover (**{high_val:.1f}%**{ratio_note}) "
                f"than {low_name} ({low_val:.1f}%). "
                f"Higher turnover indicates a more liquid, demand-driven market."
            )
        else:
            sentences.append(
                f"**Liquidity**: similar turnover across all areas (~{high_val:.1f}%/yr)."
            )

    r = best("vs_national")
    if r[0]:
        top_name, top_val, bot_name, bot_val = r
        spread   = top_val - bot_val
        top_diff = top_val - 100
        bot_diff = bot_val - 100
        top_dir  = "above" if top_diff >= 0 else "below"
        bot_dir  = "above" if bot_diff >= 0 else "below"
        if spread >= 5:
            sentences.append(
                f"**National premium**: {top_name} commands a larger premium "
                f"(**{abs(top_diff):.0f}% {top_dir}** national median) "
                f"than {bot_name} ({abs(bot_diff):.0f}% {bot_dir})."
            )
        else:
            sentences.append(
                f"**National premium**: both areas sit at a similar premium "
                f"(~{abs(top_diff):.0f}% {top_dir} national median)."
            )

    nb = [s for s in summaries if "new_build_pct" in s]
    if len(nb) >= 2:
        nb_sorted = sorted(nb, key=lambda s: s["new_build_pct"], reverse=True)
        hi, lo    = nb_sorted[0], nb_sorted[-1]
        if hi["new_build_pct"] - lo["new_build_pct"] > 5:
            sentences.append(
                f"**New-build mix**: {hi['name']} had the highest new-build share "
                f"(**{hi['new_build_pct']:.1f}%** of sales) vs {lo['name']} "
                f"({lo['new_build_pct']:.1f}%). A high new-build share can inflate "
                f"turnover figures and push median prices upward."
            )

    return sentences


def build_market_summaries(feats, poly_name_fn, poly_stats_fn, poly_prices_fn,
                           poly_uprn_count_fn, poly_mix_fn,
                           comparison_by_year, latest_year,
                           cpi, cpi_base_year,
                           from_year=None, to_year=None, adjust=True):
    from queries.price_paid_queries import real_stats_from_prices
    rows = []
    for feat in feats:
        name = poly_name_fn(feat)
        row  = {"name": name}

        if adjust and cpi:
            stats_for_calc = real_stats_from_prices(poly_prices_fn(feat), cpi, cpi_base_year)
        else:
            stats_for_calc = poly_stats_fn(feat)

        cagr_result = price_growth_cagr(stats_for_calc, latest_year, from_year, to_year)
        if cagr_result:
            row["cagr"], row["cagr_from"], row["cagr_to"] = cagr_result

        vol = price_volatility(stats_for_calc, latest_year, from_year, to_year)
        if vol is not None:
            row["volatility"] = vol

        turnover_result = annual_turnover_rate(
            poly_stats_fn(feat), poly_uprn_count_fn(feat), latest_year, from_year, to_year
        )
        if turnover_result:
            row["turnover"], row["uprn_count"] = turnover_result

        nb = average_new_build_share(poly_mix_fn(feat), latest_year, from_year, to_year)
        if nb is not None:
            row["new_build_pct"] = nb

        vs_nat = average_premium_vs_baseline(
            poly_stats_fn(feat), comparison_by_year, latest_year, from_year, to_year
        )
        if vs_nat is not None:
            row["vs_national"] = vs_nat

        rows.append(row)
    return rows
