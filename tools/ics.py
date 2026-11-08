import os
HERE=os.path.dirname(os.path.abspath(__file__))
import csv,datetime as dt,collections
rows=list(csv.DictReader(open(os.path.join(HERE,'weekdoelen.csv'))))
SHORT={'Anatomie I':'Ana','Histologie':'Histo','Celbiologie':'Celbie','Biochemie':'Biochem','Psychologie voor artsen':'Psycho'}
def esc(s): return s.replace('\\','\\\\').replace(';',r'\;').replace(',',r'\,').replace('\n',r'\n')
stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
W=collections.OrderedDict()
for r in rows: W.setdefault(r['week'],[]).append(r)
ev=[]
def add(uid,summary,desc,start=None,end=None,s=None,e=None):
    L=['BEGIN:VEVENT',f'UID:{uid}@studieplanning-ilyas',f'DTSTAMP:{stamp}']
    if s is None: L+=[f'DTSTART;VALUE=DATE:{start:%Y%m%d}',f'DTEND;VALUE=DATE:{end:%Y%m%d}','TRANSP:TRANSPARENT']
    else: L+=[f'DTSTART;TZID=Europe/Brussels:{s:%Y%m%dT%H%M%S}',f'DTEND;TZID=Europe/Brussels:{e:%Y%m%dT%H%M%S}']
    L+=[f'SUMMARY:{esc(summary)}',f'DESCRIPTION:{esc(desc)}','END:VEVENT']; ev.append(L)
for wk,gs in W.items():
    m=dt.date.fromisoformat(wk); wn=gs[0]['week_label'].split(' · ')[0]
    parts=[]
    ms=[(SHORT[g['vak']]+': ' if g['vak'] in SHORT else '')+g['doel'] for g in gs if g['type']=='Mijlpaal']
    vw=[g for g in gs if g['type']=='Verwerken']
    if vw:
        byv=collections.OrderedDict()
        for g in vw: byv.setdefault(g['vak'],[]).append(g['doel'])
        parts.append('VERWERKEN (samenvatting + vragen van Claude)\n'+'\n'.join(f"• {SHORT.get(v,v)}: {', '.join(x)}" for v,x in byv.items()))
    bh=[g for g in gs if g['type']=='Bijhouden']
    if bh: parts.append('BIJHOUDEN\n'+'\n'.join('• '+(SHORT[g['vak']]+': ' if g['vak'] in SHORT else '')+g['doel'] for g in bh))
    an=[g['doel'] for g in gs if g['type']=='Anki']
    if an: parts.append('ANKI\n• '+an[0])
    parts.append('Afvinken in je dashboard "Samenvattingen & Anki — Bach 1".')
    add(f'week-{wk}',f"{wn} · {gs[0]['thema']}",'\n\n'.join(parts),m,m+dt.timedelta(7))
    sun=m+dt.timedelta(6)
    if sun<=dt.date(2027,1,24):
        add(f'review-{sun}','Weekreview: verwerkte hoofdstukken afvinken','Vink in je dashboard af wat je deze week verwerkt hebt. Om 22u13 herplant Claude automatisch wat bleef liggen.',s=dt.datetime(sun.year,sun.month,sun.day,21,0),e=dt.datetime(sun.year,sun.month,sun.day,21,30))
tz="""BEGIN:VTIMEZONE
TZID:Europe/Brussels
BEGIN:STANDARD
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
END:DAYLIGHT
END:VTIMEZONE"""
def fold(line):
    b=line.encode(); out=[]
    while len(b)>75:
        c=75
        while (b[c]&0xC0)==0x80: c-=1
        out.append(b[:c].decode()); b=b' '+b[c:]
    out.append(b.decode()); return '\r\n'.join(out)
L=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Claude//Studieplanning Ilyas//NL','CALSCALE:GREGORIAN','X-WR-CALNAME:Studieplanning sem 1','X-WR-TIMEZONE:Europe/Brussels','REFRESH-INTERVAL;VALUE=DURATION:PT1H','X-PUBLISHED-TTL:PT1H']+tz.split('\n')
for e in ev: L+=e
L.append('END:VCALENDAR')
open(os.path.join(HERE,'..','studieplanning.ics'),'w',newline='').write('\r\n'.join(fold(l) for l in L)+'\r\n')
print(len(ev))
