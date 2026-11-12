from xml.sax.saxutils import escape
P=[]
def inn(name,lon,lat,lines): P.append(('inn',name,lon,lat,lines))
def sub(name,lon,lat,lines): P.append(('sub',name,lon,lat,lines))

# DAY 1
inn("Day 1 inn – Ena Ichikawa Inn",137.4123158,35.454506,[
 "Night 1 (Fri 13 Nov). Arrive Ena, no walking.","Day 2 walk starts here.",
 "Tel: 0573-25-2191","95-1 Ōichō, Ena, Gifu 509-7201","Facilities: Internet"])
# DAY 2
sub("D2.0 Ena Station",137.408164,35.4550961,[
 "Day 2 · Sat 14 Nov · Ena → Magome (18 km, +425 m)","Distance in: 0 km",
 "Option: JR Chuo Line train to Nakatsugawa, about 10 min. This skips the first 12 km.",
 "Then take the Kitaena bus from Nakatsugawa to Magome (see D2.1)."])
sub("D2.1 Nakatsugawa Station",137.5031352,35.5004945,[
 "Day 2 · Ena → Magome","Distance in: 12 km of 18",
 "Option: Kitaena bus to Magome, 25 min, 800 yen, cash. Weekend buses roughly hourly, 8:15–17:45.",
 "Lunch spots and a supermarket here."])
sub("D2.2 Ochiai-juku",137.5311547,35.511703,[
 "Day 2 · Ena → Magome","Distance in: ~15 km of 18 (estimate)",
 "Option: Ochiai bus stop, on the same Nakatsugawa → Magome bus line.",
 "Last exit. After this the stone-paved forest climb to Magome has no transport."])
sub("D2.3 / D3.0 Magome bus stop",137.5648672,35.5248932,[
 "Day 2 end (18 km) and Day 3 start.",
 "Day 3 option: Ontake Kotsu bus Magome → Otsumago → Tsumago → Nagiso.",
 "2026 departures from Magome: 10:55, 13:25, 15:00, 17:15. Cash."])
inn("Day 2 inn – Guest House Motomiya",137.5609182,35.5202838,[
 "End of Day 2 (Ena → Magome, 18 km). Day 3 starts here.",
 "Tel: 0573-69-2158","4944-2 Magome, Nakatsugawa, Gifu 508-0502","Facilities: Internet",
 "Nearest bus: Magome bus stop (D2.3)."])
# DAY 3
sub("D3.1 Magome Toge bus stop (top of pass)",137.584608,35.539079,[
 "Day 3 · Sun 15 Nov · Magome → O-Tsumago (10 km to Tsumago, +461 m)","Distance in: ~3 km (estimate)",
 "Option: same Magome → Nagiso bus, about 10–15 min after it leaves Magome."])
sub("D3.2 Odaki/Medaki Falls",137.5889153,35.5546314,[
 "Day 3 · Magome → O-Tsumago","Distance in: ~5.5 km (estimate)",
 "Option: Odarudaki bus stop nearby, same bus line.",
 "The falls are a 5–10 min detour off the main trail."])
sub("D3.3 / D4.0 Otsumago bus stop",137.592957,35.564724,[
 "Day 3 end (~6.5 km) and Day 4 start. Next to Maruya Inn.",
 "Day 4 option: bus to Tsumago and Nagiso Station."])
inn("Day 3 inn – Maruya Inn",137.5923279,35.5639122,[
 "End of Day 3 (Magome → O-Tsumago). Day 4 starts here.",
 "Tel: 0264-57-3117","1477 Otsumago, Nagiso, Kiso District, Nagano 399-5302","Facilities: Internet",
 "Nearest bus: Otsumago bus stop (D3.3)."])
# DAY 4
sub("D4.1 Tsumago bus stop",137.5949657,35.5790244,[
 "Day 4 · Mon 16 Nov · O-Tsumago → Nagiso → Kiso-Fukushima","Distance in: ~2 km",
 "Option: frequent buses to Nagiso Station, about 9 min, 300 yen."])
sub("D4.2 Nagiso Station",137.6084065,35.5988443,[
 "Day 4 · Distance in: ~8 km. Course B ends here (8–10 km, +107 m).",
 "Option: JR train to Kiso-Fukushima.",
 "No IC cards at this station: buy a paper ticket with cash.",
 "Course A (23 km, +714 m) carries on over Nenoue Pass with no transport until Nojiri. Take Course B if walking is a struggle."])
sub("D4.3 Nojiri Station (Course A end)",137.636199,35.6729624,[
 "Day 4 Course A end. Distance in: 23 km.","Option: JR train to Kiso-Fukushima."])
inn("Day 4 inn – Iwaya Inn",137.6973101,35.850491,[
 "End of Day 4. Day 5 starts here.",
 "Tel: 0264-22-2015","5169 Fukushima, Kiso-machi, Kiso-gun, Nagano 397-0001","Facilities: Internet, Toilet, Shower",
 "Easy walk to Kiso-Fukushima Station (D5.0)."])
# DAY 5
sub("D5.0 Kiso-Fukushima Station",137.6933476,35.8440023,[
 "Day 5 · Tue 17 Nov · Kiso-Fukushima → Kaida Plateau (10–14 km, +673 m)",
 "Skip-it-all option: Ontake Kotsu Kaida Kogen line bus to \"Yamaka Ryokan-mae\" (outside the inn), about 1 hr. You may need to change buses at Kaida Shisho (D5.3).",
 "The tour's reserved taxi to Karasawa Falls also leaves from here."])
sub("D5.1 Karasawa Falls (walk start)",137.6498313,35.9130586,[
 "Day 5 · Distance in: 0 km. The tour's reserved taxi drops you here.",
 "No bus here. The Jizo Pass section (~6 km, uphill) has no transport: commit before starting."])
sub("D5.2 Kaida Kogen Tourist Info Centre",137.6316799,35.9379712,[
 "Day 5 · Distance in: ~6 km. End of the Jizo Pass walk.",
 "Option: buses run from here. The itinerary's bus-to-the-inn option replaces the Nishino Pass walk.",
 "Café and soba nearby; Kiso horse ranch."])
sub("D5.3 Kaida Shisho bus stop",137.6003446,35.9406619,[
 "Day 5 · Bus transfer point (reached by bus from D5.2).",
 "Option: buses toward Nishino / Yamaka Ryokan-mae (the inn).",
 "The Nishino Pass walk (~4 km, steep, no transport) starts here."])
inn("Day 5 inn – Yamakanoyu",137.5841498,35.9584302,[
 "End of Day 5. Day 6 starts here (tour's reserved vehicle to the station).",
 "Tel: 0264-44-2010","3109-1 Kaidakogen Nishino, Kiso, Kiso District, Nagano 397-0302","Facilities: Internet, Toilet",
 "Bus stop at the door: Yamaka Ryokan-mae."])
# DAY 6
sub("D6.0 Yabuhara Station (walk start)",137.7844614,35.9302284,[
 "Day 6 · Wed 18 Nov · Yabuhara → Narai → Karuizawa (9 km, +373 m)","Distance in: 0 km",
 "Option: stay on the train one stop to Narai and meet the group there.",
 "Torii Pass (the whole walk) has no transport. No IC cards: paper ticket, cash."])
sub("D6.1 Narai Station (walk end)",137.8155605,35.969107,[
 "Day 6 · Distance in: 9 km.",
 "Onward: local train and shinkansen to Karuizawa (in the tour).",
 "Staffed ticket window, cash. Luggage goes to your post-tour hotel today, so you won't have it tonight."])
inn("Day 6 inn – Le Grand Kyu Karuizawa",138.6345646,36.3528081,[
 "End of Day 6. No luggage tonight. Day 7 walk starts here.",
 "Tel: 0267-41-2030","469-4 Oaza Karuizawa, Karuizawa-machi, Kitasaku-gun, Nagano 389-0102","Facilities: Internet, Toilet, Shower",
 "Walkable to Karuizawa Station (D7.0)."])
# DAY 7
sub("D7.0 Karuizawa Station",138.6353268,36.3426254,[
 "Day 7 · Thu 19 Nov · Karuizawa → Usui Pass → Yokokawa (16 km, +438 m)",
 "Option 1: JR Bus Kanto Usui line to Yokokawa Station, about 34 min, 7 a day, 520 yen cash, no IC cards.",
 "Option 2: shinkansen straight to Tokyo, about 1 hr, to your post-tour hotel where the luggage is."])
sub("D7.1 Usui Pass / Kumano Kotai Shrine",138.6561863,36.3697512,[
 "Day 7 · Distance in: ~4 km (estimate). Top of the pass.",
 "Option: the seasonal Aka Bus runs between Kyu-Karuizawa and the Usui Pass lookout from late April to late November. Check it is still running on 19 Nov.",
 "Last exit. The ~12 km descent to Yokokawa has no transport."])
sub("D7.2 Yokokawa Station (walk end)",138.737046,36.3363317,[
 "Day 7 · Distance in: 16 km. The walk ends here.",
 "Onward: JR Shin'etsu line to Takasaki, then to Tokyo.",
 "Meeting point if your companion took the Usui line bus."])

style='''    <Style id="inn"><IconStyle><color>ff2f2fd3</color><Icon><href>http://maps.google.com/mapfiles/kml/paddle/red-stars.png</href></Icon></IconStyle></Style>
    <Style id="sub"><IconStyle><color>ffd18802</color><Icon><href>http://maps.google.com/mapfiles/kml/paddle/blu-circle.png</href></Icon></IconStyle></Style>
'''
out=['<?xml version="1.0" encoding="UTF-8"?>','<kml xmlns="http://www.opengis.net/kml/2.2">','  <Document>','    <name>Nakasendo Trip – Inns and Sub-stops</name>',style.rstrip()]
for kind,name,lon,lat,lines in P:
    desc=escape("<br>".join(lines))
    out.append(f'''    <Placemark>
      <name>{escape(name)}</name>
      <styleUrl>#{kind}</styleUrl>
      <description>{desc}</description>
      <Point><coordinates>{lon},{lat},0</coordinates></Point>
    </Placemark>''')
out+=['  </Document>','</kml>']
open('/home/claude/nakasendo_full.kml','w',encoding='utf-8').write("\n".join(out)+"\n")
import xml.dom.minidom as m
d=m.parse('/home/claude/nakasendo_full.kml')
print(len(d.getElementsByTagName('Placemark')),'pins')
