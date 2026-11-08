// Identidad y permisos.
// Cloudflare Access protege todo el dominio y añade a cada petición un JWT firmado
// (cabecera Cf-Access-Jwt-Assertion). Aquí se verifica la firma y se saca el email;
// con el email se busca el rol en config/roles.json.
import ROLES from "../../config/roles.json";
import META from "../../public/data/meta.json";

// CPRO -> código de CCAA, a partir del catálogo de datos
const CPRO2CCA = {};
for (const c of META.ccaa) for (const p of c.provincias) CPRO2CCA[p] = c.cca;
export const ccaaOfProvince = cpro => CPRO2CCA[cpro];

let jwksCache = { at: 0, keys: null };
async function getKeys(teamDomain) {
  if (jwksCache.keys && Date.now() - jwksCache.at < 3600_000) return jwksCache.keys;
  const r = await fetch(`https://${teamDomain}/cdn-cgi/access/certs`);
  if (!r.ok) throw new Error("No se pudieron leer las claves de Access");
  const { keys } = await r.json();
  jwksCache = { at: Date.now(), keys };
  return keys;
}
const b64url = s => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(s.length / 4) * 4, "=")), c => c.charCodeAt(0));
const jsonPart = s => JSON.parse(new TextDecoder().decode(b64url(s)));

async function verifyAccessJWT(token, env) {
  const [h, p, sig] = token.split(".");
  if (!h || !p || !sig) throw new Error("JWT mal formado");
  const header = jsonPart(h), payload = jsonPart(p);
  const keys = await getKeys(env.ACCESS_TEAM_DOMAIN);
  const jwk = keys.find(k => k.kid === header.kid);
  if (!jwk) throw new Error("Clave desconocida");
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64url(sig), new TextEncoder().encode(`${h}.${p}`));
  if (!ok) throw new Error("Firma no válida");
  const now = Math.floor(Date.now() / 1000);
  if (payload.exp && payload.exp < now) throw new Error("Sesión caducada");
  const aud = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (env.ACCESS_AUD && !aud.includes(env.ACCESS_AUD)) throw new Error("Audiencia no válida");
  if (payload.iss && payload.iss !== `https://${env.ACCESS_TEAM_DOMAIN}`) throw new Error("Emisor no válido");
  return payload.email;
}

// Devuelve { email, roleKey, role, allowed:Set|null } o lanza error
export async function identify(request, env) {
  let email = null;
  const token = request.headers.get("Cf-Access-Jwt-Assertion");
  if (token && env.ACCESS_TEAM_DOMAIN) email = await verifyAccessJWT(token, env);
  else if (env.DEV_EMAIL) email = env.DEV_EMAIL;          // solo para pruebas en local
  if (!email) throw new Response("No autenticado", { status: 401 });
  email = email.toLowerCase();
  const roleKey = ROLES.usuarios[email] ?? ROLES.dominios[email.split("@")[1]];
  const role = roleKey && ROLES.roles[roleKey];
  if (!role) throw new Response("Tu email no tiene un rol asignado. Pide acceso al equipo de Ateneo del Dato.", { status: 403 });
  return { email, roleKey, role, allowed: role.ccaa === "*" ? null : new Set(role.ccaa) };
}
export const canSee = (who, cca) => !who.allowed || who.allowed.has(cca);
export const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "private, no-store" }
});
