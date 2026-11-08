# Mapa de prioridades FA · Generales 29N

Web de Ateneo del Dato con la prioridad territorial del Frente Amplio por comunidad, provincia, municipio y sección censal. Cada persona entra con su email y solo recibe los datos de las comunidades de su rol.

## Cómo está montado

```
navegador ──► Cloudflare Access (PIN por email) ──► Cloudflare Pages
                                                     ├─ public/            web y geometrías (sin datos electorales)
                                                     ├─ public/data/       datos, protegidos por functions/data/_middleware.js
                                                     └─ functions/api/me   quién eres y qué comunidades ves
```

- **Access** decide quién entra. **`config/roles.json`** decide qué ve cada uno.
- Los datos de `/data/*` pasan siempre por el servidor: una provincia fuera del rol devuelve 403 y los ficheros nacionales llegan recortados a las comunidades permitidas.
- Las geometrías (`public/geo`) son públicas para quien pasa Access: no llevan datos.

## Puesta en marcha (una sola vez)

### 1. Repositorio
Sube esta carpeta a un repositorio **privado** de GitHub de la organización (por ejemplo `ateneodeldato/mapas-fa`).

### 2. Cloudflare Pages
1. Cloudflare → *Workers & Pages* → *Create* → *Pages* → *Connect to Git* → elige el repositorio.
2. Configuración de build:
   - Framework preset: **None**
   - Build command: *(vacío)*
   - Build output directory: **`public`**
3. *Save and Deploy*. Quedará en `mapas-fa.pages.dev`.

### 3. Dominio
En el proyecto de Pages → *Custom domains* → *Set up a domain* → `mapas.ateneodeldato.com` (el dominio tiene que estar en Cloudflare; si no, Cloudflare indica el CNAME que hay que crear).

### 4. Cloudflare Access (login)
1. Cloudflare → *Zero Trust* → *Settings* → *Authentication* → añade **One-time PIN** como método de login.
2. *Access* → *Applications* → *Add an application* → **Self-hosted**:
   - Application domain: `mapas.ateneodeldato.com` **y** `mapas-fa.pages.dev` (y `*.mapas-fa.pages.dev` para las vistas previas). Así nadie entra por la dirección .pages.dev sin login.
   - Identity providers: One-time PIN.
3. Política **Allow** → *Include* → *Emails ending in* `@ateneodeldato.com`. Cuando entre gente de FA, añade sus emails en la misma política (*Emails*).
4. Guarda y copia el **Application Audience (AUD) Tag** (en la ficha de la aplicación).

### 5. Variables del proyecto Pages
*Settings* → *Variables and Secrets* (entorno Production y Preview):

| Variable | Valor |
|---|---|
| `ACCESS_TEAM_DOMAIN` | `TU-EQUIPO.cloudflareaccess.com` (Zero Trust → Settings → Custom pages / Team domain) |
| `ACCESS_AUD` | el AUD Tag del paso 4 |

Vuelve a desplegar (*Deployments* → *Retry deployment*). Listo.

## Día a día

### Dar acceso a alguien
1. Añade su email en la política de Access (paso 4.3), si no es de `@ateneodeldato.com`.
2. Añade su email y rol en `config/roles.json`:
   ```json
   "usuarios": { "nombre@frenteamplio.es": "andalucia" }
   ```
3. Commit y push: Pages republica solo en un minuto.

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
npm run dev        # http://localhost:8788, entras como dev@ateneodeldato.com
```
Para probar otro rol: `npx wrangler pages dev public --binding DEV_EMAIL=email@ejemplo.es`. `DEV_EMAIL` **nunca** se configura en Cloudflare.
