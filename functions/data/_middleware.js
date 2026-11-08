// Guardián de /data/*: solo deja salir los datos de las comunidades del rol.
//   /data/sscc/{cpro}.json   -> 403 si la provincia no es del rol
//   /data/municipios.json    -> filas filtradas por rol
//   /data/territorios.json   -> provincias y CCAA filtradas por rol
//   /data/meta.json          -> catálogo (sin datos electorales), libre para usuarios con rol
import { identify, canSee, ccaaOfProvince, json } from "../_lib/auth.js";

export async function onRequest(ctx) {
  const { request, env, next } = ctx;
  let who;
  try { who = await identify(request, env); }
  catch (e) { return e instanceof Response ? e : json({ error: e.message }, 401); }

  const path = new URL(request.url).pathname;
  const sscc = path.match(/^\/data\/sscc\/(\d{2})\.json$/);
  if (sscc) {
    if (!canSee(who, ccaaOfProvince(sscc[1]))) return json({ error: "Fuera de tu rol" }, 403);
    return privateCopy(await next());
  }
  if (path === "/data/meta.json") return privateCopy(await next());
  if (!who.allowed) {
    if (path === "/data/municipios.json" || path === "/data/territorios.json") return privateCopy(await next());
    return json({ error: "No encontrado" }, 404);
  }
  if (path === "/data/municipios.json") {
    const d = await (await next()).json();
    const iC = d.cols.indexOf("cpro");
    d.rows = Object.fromEntries(Object.entries(d.rows).filter(([, r]) => canSee(who, ccaaOfProvince(r[iC]))));
    return json(d);
  }
  if (path === "/data/territorios.json") {
    const d = await (await next()).json();
    d.provincias = Object.fromEntries(Object.entries(d.provincias).filter(([c]) => canSee(who, ccaaOfProvince(c))));
    d.ccaa = Object.fromEntries(Object.entries(d.ccaa).filter(([c]) => canSee(who, c)));
    return json(d);
  }
  return json({ error: "No encontrado" }, 404);
}

// Los datos nunca se guardan en cachés compartidas
function privateCopy(res) {
  const r = new Response(res.body, res);
  r.headers.set("cache-control", "private, max-age=300");
  return r;
}
