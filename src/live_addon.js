/* ================= LIVE MAP MODE (hosted copy only) =================
   Real street/topo map under the squirrels, a live GPS blue dot, and
   "set position & time to here" (keeps the start time, works out the pace). */
let LIVE = false, LMAP = null, LLAYER = null, GEO = null, GEOWATCH = null, LIVE_FITTED = false, LDRAG = false;
const LIVE_PACE_MIN = 12, LIVE_PACE_MAX = 60;

function liveInit(){
  if (LMAP || !window.LF) return !!LMAP;
  LMAP = LF.map("lmap", {zoomControl: false, attributionControl: true});
  const gsi = LF.tileLayer("https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png", {maxZoom: 18, attribution: '<a href="https://maps.gsi.go.jp/development/ichiran.html">地理院タイル (GSI Japan)</a>'});
  const gsiPale = LF.tileLayer("https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png", {maxZoom: 18, attribution: '<a href="https://maps.gsi.go.jp/development/ichiran.html">地理院タイル (GSI Japan)</a>'});
  const photo = LF.tileLayer("https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg", {maxZoom: 18, attribution: '<a href="https://maps.gsi.go.jp/development/ichiran.html">地理院タイル (GSI Japan)</a>'});
  const osm = LF.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'});
  gsi.addTo(LMAP);
  LF.control.layers({"Japan topo (GSI)": gsi, "Japan pale (GSI)": gsiPale, "Aerial photo (GSI)": photo, "OpenStreetMap": osm}, null, {position: "bottomright"}).addTo(LMAP);
  LF.control.zoom({position: "topleft"}).addTo(LMAP);
  LF.control.scale({imperial: false, position: "bottomleft"}).addTo(LMAP);
  LLAYER = LF.layerGroup().addTo(LMAP);
  return true;
}

/* lat/lng slice of a day's walk between two km marks */
function sliceLL(d, a, b){ const out = [llAt(d, a)]; d.pts.forEach(p => { if (p.km > a && p.km < b) out.push(p.ll); }); out.push(llAt(d, b)); return out; }

/* nearest point on a day's walk to a lat/lng → {km, dist (m)} (straight lines between stops) */
function snapToDay(d, ll){
  const kx = 111320 * Math.cos(ll[0] * Math.PI/180), ky = 110540;   // metres per degree
  let best = {km: 0, dist: 1e12};
  for (let i = 0; i < d.pts.length - 1; i++){
    const a = d.pts[i], b = d.pts[i+1];
    const ax = (a.ll[1]-ll[1])*kx, ay = (a.ll[0]-ll[0])*ky, bx = (b.ll[1]-ll[1])*kx, by = (b.ll[0]-ll[0])*ky;
    const vx = bx-ax, vy = by-ay, L2 = vx*vx + vy*vy || 1, f = Math.min(Math.max(-(ax*vx + ay*vy)/L2, 0), 1);
    const dist = Math.hypot(ax + f*vx, ay + f*vy);
    if (dist < best.dist) best = {km: a.km + f*(b.km - a.km), dist};
  }
  return best;
}
function snapAnyDay(ll){
  let best = null;
  ORDER.forEach(k => { const d = dayObj(k), s = snapToDay(d, ll); if (!best || s.dist < best.dist) best = {...s, day: k}; });
  return best;
}

const nowMinutes = () => { const n = new Date(); return n.getHours()*60 + n.getMinutes() + n.getSeconds()/60; };

/* put the squirrels on the trail nearest to ll, set the clock to now, keep the start time, solve the pace */
function setHere(ll){
  const s = snapAnyDay(ll), msgs = [];
  if (s.day !== S.day){ S.day = s.day; $("courseBox").hidden = S.day !== "d4"; drawChips(); }
  const d = D(), km = Math.min(Math.max(s.km, 0), total(d)), now = nowMinutes();
  if (s.dist > 1500) msgs.push(`You're about ${(s.dist/1000).toFixed(1)} km from the trail, so I used the nearest trail point.`);
  const W = walkStartOf(d), lunch = d.lunchKm != null && km > d.lunchKm + 1e-9 ? LUNCH : 0;
  const climbs = walkBetween(d, 0, km, 0);        // the climbing minutes, which don't depend on pace
  if (km < 0.05 || now <= W + climbs + lunch + 1){
    // at the start (or before the planned start): pace can't be worked out, so start walking now
    S.km = km; hereAt(now);
    msgs.push(km < 0.05 ? "You're at the start, so I set you off from here now." : `It's earlier than the planned start, so I moved today's start to fit.`);
  } else {
    let pace = (now - W - climbs - lunch) / km;
    if (pace < LIVE_PACE_MIN || pace > LIVE_PACE_MAX){
      const p2 = Math.min(Math.max(pace, LIVE_PACE_MIN), LIVE_PACE_MAX);
      msgs.push(`That works out at ${Math.round(pace)} min/km, outside the slider's ${LIVE_PACE_MIN}–${LIVE_PACE_MAX}, so I kept ${Math.round(p2)} min/km and moved today's start instead.`);
      S.pace = Math.round(p2); S.km = km; hereAt(now);
    } else {
      S.pace = Math.round(pace * 10) / 10; S.km = km; S.t = now; sync(); render();
      msgs.push(`Start kept at ${fmt(startOf(d))}. Your pace so far: about ${Math.round(pace)} min/km.`);
    }
  }
  liveToast(`📍 Set to ${fmt(now)}, ${km.toFixed(1)} km into ${d.chip}. ` + msgs.join(" "));
}

function liveToast(t){ const el = $("liveToast"); el.textContent = t; el.hidden = false; clearTimeout(el._t); el._t = setTimeout(() => el.hidden = true, 7000); }

function geoStart(){
  if (GEOWATCH != null || !navigator.geolocation) { if (!navigator.geolocation) liveToast("This browser can't share your location."); return; }
  GEOWATCH = navigator.geolocation.watchPosition(p => {
    GEO = {ll: [p.coords.latitude, p.coords.longitude], acc: p.coords.accuracy, at: Date.now()};
    if (LIVE) drawLive();
  }, e => { liveToast(e.code === 1 ? "Location is blocked. Allow location for this page in your browser settings to see the blue dot." : "Couldn't get your location yet. Trying again…"); },
  {enableHighAccuracy: true, maximumAge: 15000, timeout: 30000});
}

function iconSquirrels(){
  return LF.divIcon({className: "sq-icon", iconSize: [96, 66], iconAnchor: [74, 62],
    html: `<svg width="96" height="66" viewBox="0 0 96 66">${squirrel(22, 63, .62, "pack")}${squirrel(44, 63, .64, "scarf")}${pin(74, 62)}</svg>`});
}
function iconRide(mode){
  return LF.divIcon({className: "sq-icon", iconSize: [100, 60], iconAnchor: [50, 52], html: `<svg width="100" height="60" viewBox="0 0 100 60">${rideIcon(50, 56, mode)}</svg>`});
}

function drawLive(){
  if (!LIVE || !liveInit()) return;
  LLAYER.clearLayers();
  const d = D(), pace = S.pace, km = S.km, {fwd, back} = compute();
  const selKey = S.day === "d4" ? "d4"+S.course : S.day;
  // other days, faded
  ORDER.forEach(k => { const o = dayObj(k); if (o === d) return;
    LF.polyline(o.pts.map(p => p.ll), {color: "#5a9a5b", weight: 4, opacity: .35, dashArray: "2 7"}).addTo(LLAYER)
      .bindTooltip(o.chip, {sticky: true}); });
  // planned tour transport
  TOUR.forEach(t => { if ((t.day === "d4A" || t.day === "d4B") && t.day !== "d4"+S.course) return;
    LF.polyline([t.a, t.b], {color: "#3d5a99", weight: t.day === selKey ? 4 : 2.5, opacity: t.day === selKey ? .9 : .4, dashArray: "1 8", lineCap: "round"}).addTo(LLAYER); });
  // today's walk, coloured by escape options
  timedZones(d, pace).forEach(z => { if (z.b - z.a < 0.01) return;
    LF.polyline(sliceLL(d, z.a, z.b), {color: ZONE_COL[z.z], weight: 9, opacity: z.z === "go" ? .55 : .75, lineCap: "butt"}).addTo(LLAYER); });
  LF.polyline(d.pts.map(p => p.ll), {color: "#3b2f2a", weight: 1.5, opacity: .7, dashArray: "4 5"}).addTo(LLAYER);
  if (km > 0.01) LF.polyline(sliceLL(d, 0, km), {color: "#fff", weight: 3, opacity: .9}).addTo(LLAYER);
  const js = segAt(d, S.t), pre = !js && d.transfer && S.t < startOf(d), opt = !js && !pre;
  if (opt && fwd && fwd.dist > 0.05) LF.polyline(sliceLL(d, km, fwd.p.km), {color: "#2e8b3e", weight: 4}).addTo(LLAYER);
  if (opt && back && !back.off) LF.polyline(sliceLL(d, back.p.km, km), {color: "#e08a12", weight: 4, dashArray: "8 6"}).addTo(LLAYER);
  // stops
  d.pts.forEach(p => {
    const isF = opt && fwd && fwd.p === p, isB = opt && back && !back.off && back.p === p;
    const col = isF ? "#2e8b3e" : isB ? "#e08a12" : p.kind === "pass" ? "#5a9a5b" : "#3b2f2a";
    const t = isF ? fwd.arr : isB ? back.arr : T(d, p.km, pace);
    const o = isF ? fwd : isB ? back : null;
    let tip = `<b>${esc(p.name)}</b> · ${isF || isB ? "arrive @ " : ""}${fmt(t)}`;
    if (o && !o.noBus && o.dep != null) tip += `<br>${p.hop.mode.split(" ")[0]} ${fmt(o.dep)} · wait ${dur(o.wait)}` + (o.dep2 != null ? `<br>${p.hop.mode.split(" ")[0]} ${fmt(o.dep2)} · wait ${dur(o.dep2 - o.arr)}` : " · last one!");
    else if (o && o.noBus) tip += `<br>no ${esc(p.hop.mode.split(" ").slice(1).join(" "))} left today`;
    else if (p.hop) tip += ` ${p.hop.mode.split(" ")[0]}`;
    LF.circleMarker(p.ll, {radius: p.kind === "end" ? 8 : 6, color: col, weight: 3, fillColor: "#fff", fillOpacity: 1}).addTo(LLAYER)
      .bindTooltip(tip, {permanent: S.txt !== 1 && (isF || isB || p.kind === "end"), direction: "right", className: "live-tip" + (isF ? " f" : isB ? " b" : "") + (S.txt === 2 ? " faded" : "")});
    if (p.hop?.at) LF.polyline([p.ll, p.hop.at], {color: col, weight: 2, dashArray: "2 5"}).addTo(LLAYER);
  });
  INNS.forEach(n => LF.marker(n.ll, {icon: LF.divIcon({className: "sq-icon", html: "🏮", iconSize: [18, 18], iconAnchor: [9, 9]})}).addTo(LLAYER).bindTooltip(`Night ${n.n} · ${esc(n.name)}`));
  // the squirrels (or their train / van)
  let ll = llAt(d, km), icon = iconSquirrels(), drag = true;
  if (js){ const f = js.kind === "wait" ? 0 : (S.t - js.t0) / Math.max(js.t1 - js.t0, 1);
    ll = [js.a[0] + (js.b[0]-js.a[0])*f, js.a[1] + (js.b[1]-js.a[1])*f];
    if (js.kind === "ride"){ icon = iconRide(js.mode); drag = false; } }
  else if (pre) ll = journeyOf(d)[0].a;
  const m = LF.marker(ll, {icon, draggable: drag, zIndexOffset: 1000, keyboard: false}).addTo(LLAYER);
  m.on("dragstart", () => LDRAG = true);
  m.on("dragend", e => { LDRAG = false; const p = e.target.getLatLng(), s = snapAnyDay([p.lat, p.lng]);
    if (s.day !== S.day){ const from = ORDER.indexOf(S.day); S.day = s.day; $("courseBox").hidden = S.day !== "d4"; drawChips(); }
    setFromPos(s.km); sync(); render(); });
  // you: the blue dot
  if (GEO){
    LF.circle(GEO.ll, {radius: GEO.acc, color: "#1a73e8", weight: 1, fillColor: "#1a73e8", fillOpacity: .12, interactive: false}).addTo(LLAYER);
    const dot = LF.circleMarker(GEO.ll, {radius: 9, color: "#fff", weight: 3, fillColor: "#1a73e8", fillOpacity: 1}).addTo(LLAYER);
    const near = snapAnyDay(GEO.ll);
    dot.bindPopup(`<div class="live-pop"><b>You are here</b><br><span class="fine">±${Math.round(GEO.acc)} m · ${near.dist < 1000 ? Math.round(near.dist) + " m" : (near.dist/1000).toFixed(1) + " km"} from the ${esc(dayObj(near.day).chip)} trail</span><br><button type="button" class="live-set">📍 Set position &amp; time to here</button><div class="fine">Keeps today's start time and works out your pace.</div></div>`);
    dot.on("popupopen", e => { const b = e.popup.getElement().querySelector(".live-set"); if (b) b.onclick = () => { LMAP.closePopup(); setHere(GEO.ll); }; });
  }
  if (!LIVE_FITTED){ LIVE_FITTED = true; LMAP.fitBounds(LF.latLngBounds(d.pts.map(p => p.ll)).pad(.15)); }
}

function setLive(on){
  LIVE = on && !!window.LF;
  if (on && !window.LF){ liveToast("The live map library didn't load. Check your connection and reload."); return; }
  $("lmap").hidden = !LIVE; $("map").style.visibility = LIVE ? "hidden" : "";
  document.querySelectorAll("#zin, #zout").forEach(b => b.hidden = LIVE);
  $("zlive").textContent = LIVE ? "✏️" : "🗺️"; $("zlive").title = LIVE ? "Back to the sketch map" : "Live map with your location";
  $("zgps").hidden = !LIVE;
  if (LIVE){ liveInit(); setTimeout(() => { LMAP.invalidateSize(); drawLive(); }, 30); geoStart(); }
}
