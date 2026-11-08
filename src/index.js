// Worker del mapa de prioridades.
//   /api/me                  -> quién soy y qué comunidades veo
//   /data/sscc/{cpro}.json   -> 403 si la provincia no es del rol
//   /data/municipios.json    -> filas filtradas por rol
//   /data/territorios.json   -> provincias y CCAA filtradas por rol
//   /data/meta.json          -> catálogo (sin datos electorales)
//   resto                    -> ficheros estáticos de public/ (web y geometrías)
import { identify, canSee, ccaaOfProvince, json } from "./auth.js";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    if (path === "/api/me") return me(request, env);
    if (path.startsWith("/data/")) return data(request, env, path);
    return env.ASSETS.fetch(request);
  }
};

async function who(request, env) {
  try { return { who: await identify(request, env) }; }
  catch (e) { return { err: e instanceof Response ? e : json({ error: e.message }, 401) }; }
}

async function me(request, env) {
  const { who: w, err } = await who(request, env);
  if (err) return err;
  return json({ email: w.email, rol: w.roleKey, nombre: w.role.nombre, ccaa: w.role.ccaa });
}

async function data(request, env, path) {
  const { who: w, err } = await who(request, env);
  if (err) return err;
  const asset = () => env.ASSETS.fetch(request);

  const sscc = path.match(/^\/data\/sscc\/(\d{2})\.json$/);
  if (sscc) {
    if (!canSee(w, ccaaOfProvince(sscc[1]))) return json({ error: "Fuera de tu rol" }, 403);
    return privateCopy(await asset());
  }
  if (path === "/data/meta.json") return privateCopy(await asset());
  if (path !== "/data/municipios.json" && path !== "/data/territorios.json") return json({ error: "No encontrado" }, 404);
  if (!w.allowed) return privateCopy(await asset());

  const d = await (await asset()).json();
  if (path === "/data/municipios.json") {
    const iC = d.cols.indexOf("cpro");
    d.rows = Object.fromEntries(Object.entries(d.rows).filter(([, r]) => canSee(w, ccaaOfProvince(r[iC]))));
  } else {
    d.provincias = Object.fromEntries(Object.entries(d.provincias).filter(([c]) => canSee(w, ccaaOfProvince(c))));
    d.ccaa = Object.fromEntries(Object.entries(d.ccaa).filter(([c]) => canSee(w, c)));
  }
  return json(d);
}

// Los datos nunca se guardan en cachés compartidas
function privateCopy(res) {
  const r = new Response(res.body, res);
  r.headers.set("cache-control", "private, max-age=300");
  return r;
}
