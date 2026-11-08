// GET /api/me -> quién soy y qué comunidades veo
import { identify, json } from "../_lib/auth.js";

export async function onRequestGet({ request, env }) {
  try {
    const who = await identify(request, env);
    return json({ email: who.email, rol: who.roleKey, nombre: who.role.nombre, ccaa: who.role.ccaa });
  } catch (e) {
    if (e instanceof Response) return e;
    return json({ error: e.message }, 401);
  }
}
