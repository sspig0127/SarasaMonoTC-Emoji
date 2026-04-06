from pathlib import Path
import re
import json

OPENMOJI_DIRS = [
    Path("openmoji/black/svg"),
    Path("openmoji/color/svg"),   # 可留著，主要還是 black/svg
]

NOTO_DIRS = [
    Path("noto-emoji/svg"),
    Path("noto-emoji/third_party/region-flags/svg"),  # 若要把區域旗幟也算進去
]

SKIN_MODIFIERS = {"1F3FB", "1F3FC", "1F3FD", "1F3FE", "1F3FF"}
ZWJ = "200D"

HEX_RE = re.compile(r"^[0-9A-Fa-f]{4,6}$")


def filename_to_seq(path: Path) -> str | None:
    stem = path.stem
    # Noto format: emoji_u1F600_200D_1F525 → strip prefix, split on _
    if stem.startswith("emoji_u"):
        stem = stem[len("emoji_u"):]
        parts = stem.split("_")
    else:
        # OpenMoji format: 1F600-200D-1F525 → split on -
        parts = stem.split("-")
    cps = []
    for p in parts:
        if HEX_RE.match(p):
            cps.append(p.upper())
    if not cps:
        return None
    return "-".join(cps)


def collect_svg_sequences(dirs):
    seqs = set()
    mapping = {}
    for root in dirs:
        if not root.exists():
            continue
        for svg in root.rglob("*.svg"):
            seq = filename_to_seq(svg)
            if seq:
                seqs.add(seq)
                mapping.setdefault(seq, []).append(str(svg))
    return seqs, mapping


def has_zwj(seq: str) -> bool:
    return ZWJ in seq.split("-")


def has_skin(seq: str) -> bool:
    return any(cp in SKIN_MODIFIERS for cp in seq.split("-"))


def summarize(noto_seqs, openmoji_seqs):
    categories = {
        "all": lambda s: True,
        "zwj": has_zwj,
        "skin": has_skin,
        "zwj_or_skin": lambda s: has_zwj(s) or has_skin(s),
        "zwj_and_skin": lambda s: has_zwj(s) and has_skin(s),
    }

    result = {}
    for name, pred in categories.items():
        noto_subset = {s for s in noto_seqs if pred(s)}
        open_subset = {s for s in openmoji_seqs if pred(s)}
        inter = noto_subset & open_subset
        missing = sorted(noto_subset - open_subset)

        result[name] = {
            "noto_count": len(noto_subset),
            "openmoji_count": len(open_subset),
            "intersection_count": len(inter),
            "openmoji_cover_vs_noto_pct": round(len(inter) / len(noto_subset) * 100, 2) if noto_subset else None,
            "missing_in_openmoji_count": len(missing),
            "missing_in_openmoji_examples": missing[:50],
        }

    return result


def main():
    openmoji_seqs, openmoji_map = collect_svg_sequences(OPENMOJI_DIRS)
    noto_seqs, noto_map = collect_svg_sequences(NOTO_DIRS)

    summary = summarize(noto_seqs, openmoji_seqs)

    report = {
        "openmoji_total": len(openmoji_seqs),
        "noto_total": len(noto_seqs),
        "summary": summary,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))

    Path("output").mkdir(exist_ok=True)
    with open("output/openmoji_noto_coverage.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    noto_zwj = {s for s in noto_seqs if has_zwj(s)}
    open_zwj = {s for s in openmoji_seqs if has_zwj(s)}
    missing_zwj = sorted(noto_zwj - open_zwj)

    print("Missing ZWJ examples:")
    for s in missing_zwj[:100]:
        print(s)


if __name__ == "__main__":
    main()