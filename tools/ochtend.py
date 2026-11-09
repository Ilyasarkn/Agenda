"""Ochtendmelding: lessen van vandaag (KUL-rooster), weekdoelen en examen-aftelling
als pushmelding via ntfy. Draait elke ochtend via GitHub Actions.
Geheimen (Settings > Secrets > Actions): KUL_ICS (link naar je TimeEdit-rooster)
en NTFY_TOPIC (de naam van je ntfy-kanaal)."""
import csv, datetime as dt, os, re, sys, urllib.request
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Brussels")
HERE = os.path.dirname(os.path.abspath(__file__))
EXAMENS = [("Anatomie + histo", dt.date(2027, 1, 7)), ("Celbio", dt.date(2027, 1, 12)),
           ("Biochemie", dt.date(2027, 1, 21)), ("Psycho", dt.date(2027, 1, 26))]
KORT = {"Biochemie en moleculaire biologie": "Biochem", "Celbiologie": "Celbio", "Histologie": "Histo",
        "Anatomie I": "Ana", "Psychologie voor artsen": "Psycho", "Vaardigheden 1": "Vaardigheden"}
VAK = {"Anatomie I": "Ana", "Histologie": "Histo", "Celbiologie": "Celbio", "Biochemie": "Biochem",
       "Psychologie voor artsen": "Psycho"}
DAGEN = ["ma", "di", "wo", "do", "vr", "za", "zo"]


def lessen(ics, vandaag):
    out = []
    for blok in ics.split("BEGIN:VEVENT")[1:]:
        blok = re.sub(r"\r?\n[ \t]", "", blok)
        v = dict(re.findall(r"^([A-Z-]+)(?:;[^:]*)?:(.*)$", blok, re.M))
        try:
            s = dt.datetime.strptime(v["DTSTART"].strip(), "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc).astimezone(TZ)
        except (KeyError, ValueError):
            continue
        if s.date() != vandaag:
            continue
        titel = v.get("SUMMARY", "").replace("\\,", ",")
        if "GEEN LES" in titel.upper():
            continue
        m = re.match(r"\w+ (.+?): (\w+)", titel)
        vak, soort = (m.group(1), m.group(2)) if m else (titel[:40], "")
        naam = KORT.get(vak, vak)
        soort = {"hoorcolleges": "", "theorie": "", "practica": " practicum", "praktijk": " practicum",
                 "oefenzittingen": " oefenzitting", "werkzittingen": " werkzitting"}.get(soort, "")
        out.append((s, f"{s:%H:%M} {naam}{soort}"))
    return [t for _, t in sorted(set(out))]


def main():
    nu = dt.datetime.now(TZ)
    vandaag = nu.date()
    if len(sys.argv) > 1:
        vandaag = dt.date.fromisoformat(sys.argv[1])
    maandag = vandaag - dt.timedelta(days=vandaag.weekday())
    rows = [r for r in csv.DictReader(open(os.path.join(HERE, "weekdoelen.csv"))) if r["week"] == maandag.isoformat()]
    regels = []

    ics = os.environ.get("KUL_ICS_DATA")
    if ics is None and os.environ.get("KUL_ICS"):
        try:
            ics = urllib.request.urlopen(os.environ["KUL_ICS"], timeout=30).read().decode("utf-8", "replace")
        except Exception as e:
            regels.append(f"(rooster niet bereikbaar: {type(e).__name__})")
    if ics:
        les = lessen(ics, vandaag)
        regels.append("Lessen: " + (" · ".join(les) if les else "Geen lessen vandaag"))

    # mijlpalen van vandaag of later deze week
    def dagnr(doel):
        m = re.match(r"(ma|di|wo|do|vr|za|zo)\b", doel)
        return DAGEN.index(m.group(1)) if m else None
    vandaag_m, later_m = [], []
    for r in rows:
        if r["type"] != "Mijlpaal":
            continue
        d = dagnr(r["doel"])
        if d is None:
            continue
        doel = (VAK[r["vak"]] + " " if r["vak"] in VAK else "") + r["doel"]
        (vandaag_m if d == vandaag.weekday() else later_m if d > vandaag.weekday() else []).append(doel)
    if vandaag_m:
        regels.append("Vandaag: " + " · ".join(vandaag_m))
    if later_m:
        regels.append("Nog deze week: " + " · ".join(later_m))

    verwerk = {}
    for r in rows:
        if r["type"] == "Verwerken":
            verwerk.setdefault(VAK.get(r["vak"], r["vak"]), []).append(r["doel"])
    if verwerk:
        regels.append("Verwerken: " + " · ".join(f"{v} {', '.join(x)}" for v, x in verwerk.items()))
    bij = [r["doel"] for r in rows if r["type"] == "Bijhouden" and not r["doel"].startswith("Nieuwe lessen: SV + Anki binnen")]
    if bij:
        regels.append("Bijhouden: " + " · ".join(bij))
    anki = [r["doel"] for r in rows if r["type"] == "Anki"]
    if anki:
        m = re.match(r"(\d+)", anki[0])
        if m:
            per_dag = round(int(m.group(1)) / 7)
            regels.append(f"Anki: ±{per_dag} nieuwe vandaag ({anki[0].split(' (')[0]} deze week)")

    volgend = [(n, d) for n, d in EXAMENS if d >= vandaag]
    if volgend:
        n, d = volgend[0]
        dagen = (d - vandaag).days
        regels.append(f"Examen {n}: {'VANDAAG' if dagen == 0 else f'nog {dagen} dagen'}")

    thema = rows[0]["thema"] if rows else ""
    titel = f"{DAGEN[vandaag.weekday()].capitalize()} {vandaag.day}/{vandaag.month}" + (f" · {thema}" if thema else "")
    tekst = "\n".join(regels) or "Geen planning gevonden voor deze week."
    print(titel); print(tekst)

    topic = os.environ.get("NTFY_TOPIC")
    if topic and "--dry" not in sys.argv:
        req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=tekst.encode("utf-8"),
                                     headers={"Title": titel.encode("utf-8")})
        urllib.request.urlopen(req, timeout=30)


if __name__ == "__main__":
    main()
