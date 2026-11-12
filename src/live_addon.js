/* ================= LIVE MAP MODE (hosted copy only) =================
   Real street/topo map under the squirrels, a live GPS blue dot, and
   "set position & time to here" (keeps the start time, works out the pace). */
let LIVE = false, LMAP = null, LLAYER = null, GEO = null, GEOWATCH = null, LIVE_FITTED = false, LDRAG = false;
const LIVE_PACE_MIN = 12, LIVE_PACE_MAX = 60;

/* ---------- "Quiet" background: GSI vector tiles drawn by hand ----------
   Only contours, lakes and rivers, plus the names of villages near the trail (with romaji). */
function mvtDecode(buf){   // minimal Mapbox Vector Tile reader → {layerName: {extent, keys, values, feats:[{type, tags, geom}]}}
  const b = new Uint8Array(buf), dv = new DataView(buf), td = new TextDecoder(); let p = 0;
  const vint = () => { let r = 0, s = 0, x; do { x = b[p++]; r += (x & 0x7f) * 2**s; s += 7; } while (x & 0x80); return r; };
  const skip = w => { if (w === 0) vint(); else if (w === 1) p += 8; else if (w === 2) { const n = vint(); p += n; } else if (w === 5) p += 4; };
  const str = () => { const n = vint(), v = td.decode(b.subarray(p, p + n)); p += n; return v; };
  const packed = () => { const end = vint() + p, a = []; while (p < end) a.push(vint()); return a; };
  const layers = {};
  while (p < b.length){ const t0 = vint();
    if (t0 !== 26){ skip(t0 & 7); continue; }                     // field 3 (layers), length-delimited
    const end = vint() + p, L = {name:"", keys:[], values:[], feats:[], extent:4096};
    while (p < end){ const t1 = vint(), f = t1 >> 3;
      if (f === 1) L.name = str();
      else if (f === 2){ const fe = vint() + p, F = {type:0, tags:[], geom:[]};
        while (p < fe){ const t2 = vint(), g = t2 >> 3; if (g === 2) F.tags = packed(); else if (g === 3) F.type = vint(); else if (g === 4) F.geom = packed(); else skip(t2 & 7); }
        L.feats.push(F); }
      else if (f === 3) L.keys.push(str());
      else if (f === 4){ const ve = vint() + p; let v = null;
        while (p < ve){ const t3 = vint(), k = t3 >> 3;
          if (k === 1) v = str(); else if (k === 2){ v = dv.getFloat32(p, true); p += 4; } else if (k === 3){ v = dv.getFloat64(p, true); p += 8; }
          else if (k === 4 || k === 5) v = vint(); else if (k === 6){ const n = vint(); v = n % 2 ? -(n + 1) / 2 : n / 2; } else if (k === 7) v = !!vint(); else skip(t3 & 7); }
        L.values.push(v); }
      else if (f === 5) L.extent = vint(); else skip(t1 & 7); }
    layers[L.name] = L; }
  return layers;
}
const mvtProps = (L, F) => { const o = {}; for (let i = 0; i < F.tags.length; i += 2) o[L.keys[F.tags[i]]] = L.values[F.tags[i+1]]; return o; };
function mvtLines(F){ const out = []; let x = 0, y = 0, i = 0, cur = null; const g = F.geom;
  while (i < g.length){ const c = g[i++], id = c & 7, n = c >> 3;
    if (id === 7) continue;
    for (let k = 0; k < n; k++){ const dx = g[i++], dy = g[i++]; x += (dx >> 1) ^ -(dx & 1); y += (dy >> 1) ^ -(dy & 1);
      if (id === 1){ cur = [[x, y]]; out.push(cur); } else cur.push([x, y]); } }
  return out; }

/* kana → romaji (Hepburn, simplified) so the village names are readable */
const KANA = Object.fromEntries("あa いi うu えe おo かka きki くku けke こko さsa しshi すsu せse そso たta ちchi つtsu てte とto なna にni ぬnu ねne のno はha ひhi ふfu へhe ほho まma みmi むmu めme もmo やya ゆyu よyo らra りri るru れre ろro わwa をo んn がga ぎgi ぐgu げge ごgo ざza じji ずzu ぜze ぞzo だda ぢji づzu でde どdo ばba びbi ぶbu べbe ぼbo ぱpa ぴpi ぷpu ぺpe ぽpo ぁa ぃi ぅu ぇe ぉo".split(" ").map(s => [s[0], s.slice(1)]));
function romaji(k){
  k = String(k || "").replace(/[ァ-ヶ]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x60)); let out = "";
  for (let i = 0; i < k.length; i++){ const c = k[i], n = k[i+1];
    if (c === "っ"){ const r = KANA[n] || ""; out += r.startsWith("ch") ? "t" : r[0] || ""; continue; }
    if (KANA[c] && n && "ゃゅょ".includes(n)){ const r = KANA[c], v = {"ゃ":"a","ゅ":"u","ょ":"o"}[n]; out += (/^(shi|chi|ji)$/.test(r) ? r.slice(0, -1) : r.slice(0, -1) + "y") + v; i++; continue; }
    out += KANA[c] ?? ""; }
  out = out.replace(/ou/g, "o").replace(/uu/g, "u").replace(/oo/g, "o");
  return out ? out[0].toUpperCase() + out.slice(1) : ""; }

let TRAIL_SEGS = null;   // every day's walking path, for "is this village near the trail?"
function nearTrail(ll, m){
  if (!TRAIL_SEGS){ TRAIL_SEGS = []; Object.values(DAYS).forEach(d => d.pts.forEach((p, i) => { const line = TRAIL[d.id]?.[i] || []; for (let j = 1; j < line.length; j++) TRAIL_SEGS.push([line[j-1], line[j]]); })); }
  const kx = 111320 * Math.cos(ll[0] * Math.PI/180), ky = 110540;
  return TRAIL_SEGS.some(([a, b]) => { const ax = (a[1]-ll[1])*kx, ay = (a[0]-ll[0])*ky, bx = (b[1]-ll[1])*kx, by = (b[0]-ll[0])*ky;
    if (Math.min(ax, bx) > m || Math.max(ax, bx) < -m || Math.min(ay, by) > m || Math.max(ay, by) < -m) return false;
    const vx = bx-ax, vy = by-ay, f = Math.min(Math.max(-(ax*vx + ay*vy)/(vx*vx + vy*vy || 1), 0), 1);
    return Math.hypot(ax + f*vx, ay + f*vy) <= m; });
}
const QUIET_URL = (z, x, y) => `https://cyberjapandata.gsi.go.jp/xyz/experimental_bvmap/${z}/${x}/${y}.pbf`;
const GSI_ATTR = '<a href="https://maps.gsi.go.jp/development/ichiran.html">地理院タイル (GSI Japan)</a>';
function makeQuietLayer(){
  const labels = LF.layerGroup(), byTile = new Map(), live = new Map(), stat = tileStat("quiet");
  const Q = LF.GridLayer.extend({
    createTile(c, done){
      const cv = document.createElement("canvas"), r = Math.min(window.devicePixelRatio || 1, 2), sz = this.getTileSize();
      cv.width = sz.x * r; cv.height = sz.y * r;
      const ctx = cv.getContext("2d"); ctx.fillStyle = "#fbf6ec"; ctx.fillRect(0, 0, cv.width, cv.height);
      stat.wait++; let settled = false;
      const finish = e => { if (settled) return; settled = true; stat.wait--; if (e) tileFailed("quiet", e); else { stat.ok++; tileOk(); } done(null, cv); };
      const ac = window.AbortController ? new AbortController() : null, timer = setTimeout(() => { if (ac) ac.abort(); finish(new Error("timed out")); }, 15000);
      fetch(QUIET_URL(c.z, c.x, c.y), ac ? {signal: ac.signal} : {}).then(res => { if (res.status === 404) return null; if (!res.ok) throw new Error("tile HTTP " + res.status); return res.arrayBuffer(); }).then(buf => {
        if (buf) quietDraw(ctx, mvtDecode(buf), cv.width, r, c, this, labels, byTile, live); clearTimeout(timer); finish();
      }).catch(e => { clearTimeout(timer); finish(e); });
      return cv; },
    onAdd(map){ LF.GridLayer.prototype.onAdd.call(this, map); labels.addTo(map); },
    onRemove(map){ LF.GridLayer.prototype.onRemove.call(this, map); map.removeLayer(labels); }
  });
  const q = new Q({maxNativeZoom: 16, minNativeZoom: 4, maxZoom: 18, attribution: GSI_ATTR});
  q.on("tileunload", e => { const k = `${e.coords.z}/${e.coords.x}/${e.coords.y}`;
    (byTile.get(k) || []).forEach(id => { const L = live.get(id); if (L && --L.n <= 0){ labels.removeLayer(L.m); live.delete(id); } }); byTile.delete(k); });
  return q;
}
function quietDraw(ctx, Ls, px, r, c, layer, labels, byTile, live){
  ctx.lineJoin = ctx.lineCap = "round";
  const each = (name, fn) => { const L = Ls[name]; if (!L) return; const s = px / L.extent; L.feats.forEach(F => fn(mvtLines(F), mvtProps(L, F), s, L.extent)); };
  const trace = (lines, s, close) => { ctx.beginPath(); lines.forEach(l => { l.forEach(([x, y], i) => i ? ctx.lineTo(x*s, y*s) : ctx.moveTo(x*s, y*s)); if (close) ctx.closePath(); }); };
  each("contour", (ls, p, s) => { const idx = c.z >= 13 ? p.alti % 50 === 0 : p.alti % 500 === 0;
    trace(ls, s); ctx.strokeStyle = idx ? "rgba(150,108,70,.55)" : "rgba(170,130,92,.32)"; ctx.lineWidth = (idx ? 1.1 : .6) * r; ctx.stroke(); });
  each("waterarea", (ls, p, s) => { trace(ls, s, true); ctx.fillStyle = "#cfe4f1"; ctx.fill("evenodd"); ctx.strokeStyle = "#a9cde6"; ctx.lineWidth = .8 * r; ctx.stroke(); });
  each("river", (ls, p, s) => { trace(ls, s); ctx.strokeStyle = "#9fc8e3"; ctx.lineWidth = 1.4 * r; ctx.stroke(); });
  const key = `${c.z}/${c.x}/${c.y}`, ids = [], n = 2 ** c.z;
  each("label", (ls, p, s, ext) => {
    if (p.annoCtg !== 210 && p.annoCtg !== 220 || !ls[0]?.[0]) return;   // 210/220 = village and hamlet names
    const [x, y] = ls[0][0], lon = (c.x + x/ext) / n * 360 - 180, lat = Math.atan(Math.sinh(Math.PI * (1 - 2 * (c.y + y/ext) / n))) * 180 / Math.PI;
    if (!nearTrail([lat, lon], 1200)) return;
    const id = `${String(p.knj).replace(/^大?字/, "")}@${lat.toFixed(3)},${lon.toFixed(3)}`; ids.push(id);
    if (live.has(id)) { live.get(id).n++; return; }
    const knj = String(p.knj || "").replace(/^大?字/, ""), ro = romaji(String(p.kana || "").replace(/^(おお)?あざ/, "")), html = `<span class="qlab">${esc(ro || knj)}${ro ? ` <small>${esc(knj)}</small>` : ""}</span>`;
    const m = LF.marker([lat, lon], {icon: LF.divIcon({className: "qlab-icon", html, iconSize: [0, 0]}), pane: "qlabels", interactive: false, keyboard: false});
    live.set(id, {m, n: 1}); labels.addLayer(m);
  });
  byTile.set(key, ids);
}

let BASES = null, BASE_ON = null, SKYR = null;
/* tile health per background, shown in ☰ so a blank map can be diagnosed on the phone itself */
const TILES = {};
const tileStat = k => TILES[k] = TILES[k] || {ok: 0, bad: 0, wait: 0, err: ""};
const FALLBACK = {quiet: "pale", pale: "osm", topo: "osm", photo: "osm"};
function tileOk(){ statusLine(); }
function tileFailed(k, e){ const st = tileStat(k); st.bad++; st.err = st.err || String(e && e.message || e || "tile error"); statusLine();
  if (st.ok === 0 && st.bad >= 4 && BASES && BASE_ON === BASES[k] && FALLBACK[k]){   // nothing has drawn: don't leave a blank map
    const nx = FALLBACK[k]; setBase(nx, true); liveToast(`The ${k} map couldn't load here (${st.err}), so I've switched to ${nx}. ☰ → Live map to change.`); } }
function statusLine(){ const el = $("mStat"); if (!el || !LMAP) return;
  const on = Object.keys(BASES || {}).find(k => BASES[k] === BASE_ON);
  el.textContent = "Map tiles: " + (Object.entries(TILES).filter(([k, s]) => k === on || s.ok || s.bad).map(([k, s]) =>
    `${k}${k === on ? " (on)" : ""} ${s.ok} shown, ${s.bad} failed, ${s.wait} waiting${s.err ? ` – ${s.err}` : ""}`).join(" · ") || "none yet"); }
function watchTiles(k, layer){ const st = tileStat(k);
  layer.on("tileloadstart", () => { st.wait++; statusLine(); });
  layer.on("tileload", () => { st.wait = Math.max(0, st.wait - 1); st.ok++; tileOk(); });
  layer.on("tileerror", () => { st.wait = Math.max(0, st.wait - 1); tileFailed(k, "image failed"); });
  return layer; }
function setBase(k, auto){
  if (!LMAP) return;
  const b = BASES[k] || BASES.quiet; if (b === BASE_ON) return;
  if (auto){ S.base = k; menuSync(); }   // automatic fallback: shown in the menu, not saved
  if (BASE_ON) LMAP.removeLayer(BASE_ON);
  BASE_ON = b.addTo(LMAP); BASE_ON.bringToBack();
}
function liveInit(){
  if (LMAP || !window.LF) return !!LMAP;
  LMAP = LF.map("lmap", {zoomControl: false, attributionControl: true});
  LMAP.createPane("qlabels").style.zIndex = 390;                       // village names: under the route lines
  const sky = LMAP.createPane("sky"); sky.style.zIndex = 300; sky.style.pointerEvents = "none"; sky.classList.add("skypane");
  SKYR = LF.svg({pane: "sky", padding: .5});
  BASES = {
    quiet: makeQuietLayer(),
    pale: watchTiles("pale", LF.tileLayer("https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png", {maxZoom: 18, attribution: GSI_ATTR})),
    topo: watchTiles("topo", LF.tileLayer("https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png", {maxZoom: 18, attribution: GSI_ATTR})),
    photo: watchTiles("photo", LF.tileLayer("https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg", {maxZoom: 18, attribution: GSI_ATTR})),
    osm: watchTiles("osm", LF.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}))
  };
  setBase(S.base);
  // no Leaflet zoom control: the map's own ＋ / － buttons zoom the live map too, leaving the top left for the weather strip
  LF.control.scale({imperial: false, position: "bottomleft"}).addTo(LMAP);
  LLAYER = LF.layerGroup().addTo(LMAP);
  LMAP.on("zoomend", placeKids);   // the kids keep the same on-screen spacing at every zoom
  LMAP.attributionControl.addAttribution('trail <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap</a>');
  return true;
}

/* nearest point on a day's walk to a lat/lng → {km, dist (m)}, along the drawn path (walking path or straight lines) */
function snapToDay(d, ll){
  const kx = 111320 * Math.cos(ll[0] * Math.PI/180), ky = 110540;   // metres per degree
  let best = {km: 0, dist: 1e12};
  const g = geomOf(d);
  for (let i = 0; i < g.length - 1; i++){
    const a = g[i], b = g[i+1];
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
function iconPin(){ return LF.divIcon({className: "sq-icon", iconSize: [48, 66], iconAnchor: [24, 62], html: `<svg width="48" height="66" viewBox="0 0 48 66">${pin(24, 62)}</svg>`}); }
function iconKid(acc, sc){ return LF.divIcon({className: "sq-icon", iconSize: [40, 40], iconAnchor: [24, 34], html: `<svg width="40" height="40" viewBox="0 0 40 40">${squirrel(20, 37, sc, acc)}</svg>`}); }
/* the two grown-up kids trail behind mum along today's path, a fixed number of screen pixels back (like the sketch map) */
let KIDS = null;
function kidsLL(d, km){
  const pts = sliceLL(d, 0, Math.max(km, 0.0001)).reverse().map(q => LMAP.latLngToContainerPoint(q));
  const back = dist => { let left = dist;
    for (let i = 0; i < pts.length - 1; i++){ const a = pts[i], b = pts[i+1], l = a.distanceTo(b);
      if (l >= left){ const f = left / (l || 1); return LMAP.containerPointToLatLng([a.x + (b.x-a.x)*f, a.y + (b.y-a.y)*f]); } left -= l; }
    return LMAP.containerPointToLatLng(pts.at(-1)); };
  const o = pts[0]; let k1 = back(24), k2 = back(46);
  const px = q => LMAP.latLngToContainerPoint(q);
  if (px(k1).distanceTo(o) < 8) k1 = LMAP.containerPointToLatLng([o.x - 16, o.y + 2]);          // at the very start: huddle beside mum
  if (px(k2).distanceTo(px(k1)) < 8) k2 = LMAP.containerPointToLatLng([px(k1).x - 16, px(k1).y + 1]);
  return [k1, k2];
}
function placeKids(){ if (!KIDS || !LMAP || !LMAP._loaded) return;   // no view yet: the fit that follows fires zoomend
  const [a, b] = kidsLL(D(), S.km); KIDS[0].setLatLng(a); KIDS[1].setLatLng(b); }
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
    LF.polyline(lineLL(o), {color: "#5a9a5b", weight: 4, opacity: .35, dashArray: "2 7"}).addTo(LLAYER)
      .bindTooltip(o.chip, {sticky: true}); });
  // planned tour transport
  TOUR.forEach(t => { if ((t.day === "d4A" || t.day === "d4B") && t.day !== "d4"+S.course) return;
    LF.polyline([t.a, ...(t.via || []), t.b], {color: "#3d5a99", weight: t.day === selKey ? 4 : 2.5, opacity: t.day === selKey ? .9 : .4, dashArray: "1 8", lineCap: "round"}).addTo(LLAYER); });
  // the daylight band (blurred by CSS on its pane), under everything else
  if (S.sky){ const q = skySamples(d, 120);
    for (let i = 0; i < q.length-1; i++) LF.polyline([q[i].ll, q[i+1].ll], {pane: "sky", renderer: SKYR, color: q[i].col, weight: 30, opacity: 1, lineCap: "round", interactive: false}).addTo(LLAYER); }
  // today's walk, coloured by escape options
  timedZones(d, pace).forEach(z => { if (z.b - z.a < 0.01) return;
    LF.polyline(sliceLL(d, z.a, z.b), {color: ZONE_COL[z.z], weight: 9, opacity: z.z === "go" ? .55 : .75, lineCap: "butt"}).addTo(LLAYER); });
  LF.polyline(lineLL(d), {color: "#3b2f2a", weight: 1.5, opacity: .7, dashArray: "4 5"}).addTo(LLAYER);
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
    const ends = p === d.pts[0] || p === d.pts.at(-1);   // start place and end village always named
    let tip = `<b>${esc(isF || isB ? p.name : placeName(d, p))}</b> · ${isF || isB ? "arrive @ " : ""}${fmt(t)}`;
    if (o && !o.noBus && o.dep != null) tip += `<br>${p.hop.mode.split(" ")[0]} ${fmt(o.dep)} · wait ${dur(o.wait)}` + (o.dep2 != null ? `<br>${p.hop.mode.split(" ")[0]} ${fmt(o.dep2)} · wait ${dur(o.dep2 - o.arr)}` : " · last one!");
    else if (o && o.noBus) tip += `<br>no ${esc(p.hop.mode.split(" ").slice(1).join(" "))} left today`;
    else if (p.hop) tip += ` ${p.hop.mode.split(" ")[0]}`;
    LF.circleMarker(p.ll, {radius: p.kind === "end" ? 8 : 6, color: col, weight: 3, fillColor: "#fff", fillOpacity: 1}).addTo(LLAYER)
      .bindTooltip(tip, {permanent: S.txt !== 1 && (isF || isB || ends), direction: ends && !isF && !isB ? "left" : "right", className: "live-tip" + (isF ? " f" : isB ? " b" : "") + (S.txt === 2 ? " faded" : "")});
    if (p.hop?.at) LF.polyline([p.ll, p.hop.at], {color: col, weight: 2, dashArray: "2 5"}).addTo(LLAYER);
  });
  // the bus/train you'd catch: dashed line through the stops it passes, a dot where you'd get off, grey if the same train runs on
  const tourLeg = o => TOUR.some(t => t.day === selKey && near(t.a, o.p.hop.at || o.p.ll) && near(t.b, o.p.hop.toLL));
  const rideLine = (o, side, col) => { if (tourLeg(o)) return; const h = o.p.hop, a = h.at || o.p.ll, b = h.toLL;
    let pts = [a, ...(h.via || []), b];
    if (pts.length === 2){ const k = Math.cos(a[0]*Math.PI/180), vx = (b[1]-a[1])*k, vy = b[0]-a[0], off = .12*side;   // a gentle bow, to one side
      pts = [a, [(a[0]+b[0])/2 + vx*off, (a[1]+b[1])/2 - vy*off/k], b]; }
    const line = smoothThrough(pts);
    LF.polyline(line, {color: "#fffdf8", weight: 7, opacity: .9, interactive: false}).addTo(LLAYER);
    LF.polyline(line, {color: col, weight: 4, dashArray: "9 6", interactive: false}).addTo(LLAYER);
    (h.via || []).forEach(v => LF.circleMarker(v, {radius: 4, color: col, weight: 2, fillColor: "#fff", fillOpacity: 1, interactive: false}).addTo(LLAYER));
    const end = LF.circleMarker(b, {radius: 6, color: "#fff", weight: 2, fillColor: col, fillOpacity: 1}).addTo(LLAYER);
    if (o.dep != null && h.ride) end.bindTooltip(`${side > 0 ? "➡️" : "↩️"} ${h.mode.split(" ")[0]} at ${esc(h.to)} ~${fmt(o.dep + h.ride)}`, {permanent: S.txt !== 1, direction: "right", className: "live-tip" + (side > 0 ? " f" : " b") + (S.txt === 2 ? " faded" : "")});
    if (h.on?.length){ LF.polyline([b, ...h.on.map(n => n.ll)], {color: "#6f6259", weight: 1.5, opacity: .85, interactive: false}).addTo(LLAYER);
      const last = h.on.at(-1); LF.circleMarker(last.ll, {radius: 3, color: "#6f6259", weight: 1, fillColor: "#6f6259", fillOpacity: 1}).addTo(LLAYER)
        .bindTooltip(`same ${h.mode.split(" ")[0]} on to ${esc(last.name)}${h.est ? " ≈" : ""}`, {direction: "right"}); } };
  const rideF = opt && fwd && !fwd.noBus && !tourLeg(fwd), rideB = opt && back && !back.off && (!fwd || back.p !== fwd.p) && !tourLeg(back);
  const shared = rideF && rideB ? sharedRide(fwd, back) : null;
  if (shared){   // both ways out end up on the same bus/train: one line, orange-and-green where they share it
    const N = 10, poly = smoothThrough(shared.nodes, N), cut = shared.k * N, own = shared.long === fwd ? "#2e8b3e" : "#e08a12";
    LF.polyline(poly, {color: "#fffdf8", weight: 7, opacity: .9, interactive: false}).addTo(LLAYER);
    LF.polyline(poly.slice(0, cut + 1), {color: own, weight: 4, dashArray: "9 6", interactive: false}).addTo(LLAYER);
    LF.polyline(poly.slice(cut), {color: "#e08a12", weight: 4, dashArray: "9 9", dashOffset: "9", lineCap: "butt", interactive: false}).addTo(LLAYER);
    LF.polyline(poly.slice(cut), {color: "#2e8b3e", weight: 4, dashArray: "9 9", lineCap: "butt", interactive: false}).addTo(LLAYER);
    shared.nodes.slice(1, -1).forEach((v, i) => LF.circleMarker(v, {radius: 4, color: i + 1 < shared.k ? own : "#e08a12", weight: 2, fillColor: i + 1 < shared.k ? "#fff" : "#2e8b3e", fillOpacity: 1, interactive: false}).addTo(LLAYER));
    const end = LF.circleMarker(shared.nodes.at(-1), {radius: 7, color: "#e08a12", weight: 2.5, fillColor: "#2e8b3e", fillOpacity: 1}).addTo(LLAYER);
    const tip = (o, side) => o.dep != null && o.p.hop.ride ? `${side > 0 ? "➡️" : "↩️"} ${o.p.hop.mode.split(" ")[0]} at ${esc(o.p.hop.to)} ~${fmt(o.dep + o.p.hop.ride)}` : "";
    end.bindTooltip([tip(fwd, 1), tip(back, -1)].filter(Boolean).join("<br>"), {permanent: S.txt !== 1, direction: "right", className: "live-tip" + (S.txt === 2 ? " faded" : "")});
  } else {
    if (rideF) rideLine(fwd, 1, "#2e8b3e");
    if (rideB) rideLine(back, -1, "#e08a12");
  }
  const skip = skipOf(D(), S.t);
  if (skip){   // Day 5: the bus that skips the walk
    const s = skip.s, line = skipLL(d, s);
    LF.polyline(line, {color: "#fffdf8", weight: 7, opacity: .9, interactive: false}).addTo(LLAYER);
    LF.polyline(line, {color: "#7b5ea7", weight: 4, dashArray: "9 6", interactive: false}).addTo(LLAYER);
    (s.via || []).forEach(v => LF.circleMarker(v, {radius: 4, color: "#7b5ea7", weight: 2, fillColor: "#fff", fillOpacity: 1, interactive: false}).addTo(LLAYER));
    LF.circleMarker(s.fromLL, {radius: 6, color: "#7b5ea7", weight: 3, fillColor: "#fff", fillOpacity: 1}).addTo(LLAYER).bindTooltip(`🚏 ${esc(s.from)}`);
    const end = LF.circleMarker(s.toLL, {radius: 7, color: "#fff", weight: 2, fillColor: "#7b5ea7", fillOpacity: 1}).addTo(LLAYER);
    if (skip.dep != null) end.bindTooltip(`🚌 ${s.tag}: ${fmt(skip.dep)} → ${esc(s.to)} ${s.arrEst ? "≈" : ""}${fmt(skip.at)}`, {permanent: S.txt !== 1, direction: "right", className: "live-tip" + (S.txt === 2 ? " faded" : "")});
  }
  INNS.forEach(n => LF.marker(n.ll, {icon: LF.divIcon({className: "sq-icon", html: "🏮", iconSize: [18, 18], iconAnchor: [9, 9]})}).addTo(LLAYER).bindTooltip(`Night ${n.n} · ${esc(n.name)}`));
  // the squirrels (or their train / van)
  let ll = llAt(d, km), icon = iconPin(), drag = true, walking = true;
  if (js){ const f = js.kind === "wait" ? 0 : (S.t - js.t0) / Math.max(js.t1 - js.t0, 1);
    ll = alongPoly([js.a, ...(js.via || []), js.b], f);
    icon = js.kind === "ride" ? iconRide(js.mode) : iconSquirrels(); drag = js.kind !== "ride"; walking = false; }
  else if (pre){ ll = journeyOf(d)[0].a; icon = iconSquirrels(); walking = false; }
  KIDS = walking ? [iconKid("scarf", .64), iconKid("pack", .62)].map(ic => LF.marker(llAt(d, km), {icon: ic, interactive: false, keyboard: false, zIndexOffset: 900}).addTo(LLAYER)) : null;
  placeKids();
  const m = LF.marker(ll, {icon, draggable: drag, zIndexOffset: 1000, keyboard: false}).addTo(LLAYER);
  // dragging keeps the squirrels on the trail all the way (like the sketch map): snap on every move
  // stay on today's walk unless another day is clearly nearer (where days meet, e.g. Magome, today wins),
  // and land exactly on the day's start or finish when the finger is within a few pixels of it
  const snapDrag = p => { const ll = [p.lat, p.lng], mpp = 40075016.7 * Math.cos(p.lat * Math.PI/180) / Math.pow(2, LMAP.getZoom() + 8);
    let s = {...snapToDay(D(), ll), day: S.day};
    ORDER.forEach(k => { if (k === S.day) return; const o = snapToDay(dayObj(k), ll); if (o.dist + 8 * mpp < s.dist) s = {...o, day: k}; });
    if (s.day !== S.day){ S.day = s.day; $("courseBox").hidden = S.day !== "d4"; drawChips(); }
    const d = D(), cp = LMAP.latLngToContainerPoint(p), px = q => cp.distanceTo(LMAP.latLngToContainerPoint(q));
    setFromPos(snapEnds(d, s.km, px(llAt(d, 0)), px(llAt(d, total(d))))); sync(); render(); return llAt(D(), S.km); };
  m.on("dragstart", () => LDRAG = true);
  m.on("drag", e => { m.setLatLng(snapDrag(e.target.getLatLng())); placeKids(); });
  m.on("dragend", e => { snapDrag(e.target.getLatLng()); LDRAG = false; render(); });
  // you: the blue dot
  if (GEO){
    LF.circle(GEO.ll, {radius: GEO.acc, color: "#1a73e8", weight: 1, fillColor: "#1a73e8", fillOpacity: .12, interactive: false}).addTo(LLAYER);
    const dot = LF.circleMarker(GEO.ll, {radius: 9, color: "#fff", weight: 3, fillColor: "#1a73e8", fillOpacity: 1}).addTo(LLAYER);
    const near = snapAnyDay(GEO.ll);
    dot.bindPopup(`<div class="live-pop"><b>You are here</b><br><span class="fine">±${Math.round(GEO.acc)} m · ${near.dist < 1000 ? Math.round(near.dist) + " m" : (near.dist/1000).toFixed(1) + " km"} from the ${esc(dayObj(near.day).chip)} trail</span><br><button type="button" class="live-set">📍 Set position &amp; time to here</button><div class="fine">Keeps today's start time and works out your pace.</div></div>`);
    dot.on("popupopen", e => { const b = e.popup.getElement().querySelector(".live-set"); if (b) b.onclick = () => { LMAP.closePopup(); setHere(GEO.ll); }; });
  }
  if (!LIVE_FITTED){ LIVE_FITTED = true; LMAP.fitBounds(LF.latLngBounds(lineLL(d)).pad(.15)); }
}

function setLive(on){
  LIVE = on && !!window.LF;
  if (on && !window.LF){ liveToast("The live map library didn't load. Check your connection and reload."); return; }
  $("lmap").hidden = !LIVE; $("map").style.visibility = $("sky").style.visibility = LIVE ? "hidden" : "";
  $("zlive").innerHTML = LIVE ? "✏️<small>Sketch</small>" : "🗺️<small>Live</small>"; $("zlive").classList.toggle("on", LIVE);
  $("zlive").title = LIVE ? "Back to the sketch map" : "Live map with your location"; $("zlive").setAttribute("aria-label", $("zlive").title);
  $("zgps").hidden = !LIVE;
  if (LIVE){ liveInit(); setTimeout(() => { LMAP.invalidateSize(); drawLive(); }, 30); geoStart(); }
}
