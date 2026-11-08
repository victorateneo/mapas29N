# Mapa de prioridades FA · Generales 29N

Web de Ateneo del Dato con la prioridad territorial del Frente Amplio por comunidad, provincia, municipio y sección censal. Cada persona entra con su email y solo recibe los datos de las comunidades de su rol.

## Cómo está montado

```
navegador ──► Cloudflare Access (PIN por email) ──► Worker «mapas29n»
                                                     ├─ src/index.js       /api/me y control de /data/* por rol
                                                     ├─ public/            web y geometrías (sin datos electorales)
                                                     └─ public/data/       datos; solo salen a través del Worker
```

- **Access** decide quién entra. **`config/roles.json`** decide qué ve cada uno.
- El Worker atiende todas las peticiones (`run_worker_first`): una provincia fuera del rol devuelve 403 y los ficheros nacionales salen recortados a las comunidades permitidas.
- No hay dirección `*.workers.dev`: solo se entra por el dominio propio, protegido con Access.

## Puesta en marcha (una sola vez)

1. **Worker conectado al repo.** *Workers & Pages* → *Create* → *Import a repository* → `mapas29N`. Deploy command: `npx wrangler deploy` (la configuración está en `wrangler.jsonc`). Cada push a `main` se publica solo.
2. **Dominio.** En el Worker → *Settings* → *Domains & Routes* → *Add* → *Custom domain* → `mapas.ateneodeldato.com`.
3. **Access.** *Zero Trust* → *Settings* → *Authentication*: añade **One-time PIN**. Después *Access* → *Applications* → *Add an application* → **Self-hosted** → dominio `mapas.ateneodeldato.com`, política **Allow** con *Emails ending in* `@ateneodeldato.com`. Copia el **Application Audience (AUD) Tag**.
4. **Variables.** En el Worker → *Settings* → *Variables and Secrets*: `ACCESS_TEAM_DOMAIN` = `TU-EQUIPO.cloudflareaccess.com` y `ACCESS_AUD` = el AUD Tag. Vuelve a desplegar.

## Día a día

### Dar acceso a alguien
1. Añade su email en la política de Access (paso 3), si no es de `@ateneodeldato.com`.
2. Añade su email y rol en `config/roles.json`:
   ```json
   "usuarios": { "nombre@frenteamplio.es": "andalucia" }
   ```
3. Commit y push: el Worker se republica solo en un minuto.

Los roles se definen en el mismo fichero con códigos INE de comunidad (`"*"` = todas). Códigos: 01 Andalucía · 02 Aragón · 03 Asturias · 04 Illes Balears · 05 Canarias · 06 Cantabria · 07 Castilla y León · 08 Castilla-La Mancha · 09 Cataluña · 10 C. Valenciana · 11 Extremadura · 12 Galicia · 13 Madrid · 14 Murcia · 15 Navarra · 16 País Vasco · 17 La Rioja · 18 Ceuta · 19 Melilla.

### Cambiar el cálculo de prioridades
Los parámetros (pesos provinciales, umbrales, reparto 10/10/20/30/30) están al principio de `pipeline/calculo_prioridades.py`.

```bash
pip install pandas openpyxl numpy
python3 pipeline/build_data.py     # regenera public/data/
python3 pipeline/build_excel.py    # regenera salida/Prioridades_FA_29N_base.xlsx
```
Commit y push de `public/data/`.

Entradas en `pipeline/inputs/`: `prioridades_sscc.xlsx`, `Prioridad_provincias_FA_29N_Ateneo.xlsx`, `cod_pos_sscc.csv`.

### Geometrías de 2023
Ahora mismo `public/geo` usa la cartografía de secciones de 2019 (faltan 395 secciones creadas después). Para pasar a la de 2023:
```bash
bash pipeline/build_geo.sh ruta/SECC_CE_20230101.shp
python3 pipeline/build_data.py
```

### Marca
- Tipografía de titulares: copia `Gigalypse.woff2` en `public/assets/fonts/`. Mientras no esté, se usa Montserrat.
- Logos: `public/assets/logos/` (pendiente de sustituir los textos de la cabecera).

### Probar en local
```bash
npm install
npm run dev        # http://localhost:8787, entras como dev@ateneodeldato.com
```
Para probar otro rol: `npx wrangler dev --var DEV_EMAIL:email@ejemplo.es`. `DEV_EMAIL` **nunca** se configura en Cloudflare.
