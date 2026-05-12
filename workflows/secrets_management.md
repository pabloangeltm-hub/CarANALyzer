# SOP — Gestión de Secretos en Producción

**Tarea:** F5-T20 | Owner: Claude Code | Fecha: 2026-05-08  
**Alcance:** Comparativa Doppler.com vs .env encriptado (sops+age) + recomendación para VPS Agartha

---

## 1. El Problema

Agartha gestiona secretos de alta sensibilidad:

| Categoría | Variables |
|-----------|-----------|
| Pagos | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` |
| IA / Scraping | `SCRAPINGBEE_API_KEY`, `BRIGHTDATA_KEY`, `TWOCAPTCHA_API_KEY` |
| Mensajería | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| Auth | `JWT_SECRET`, `DATABASE_URL` |
| Cloud | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (backups S3/R2) |
| OAuth | `GOOGLE_OAUTH_CLIENT_SECRET` |

Requisitos para producción VPS:
- Secretos **nunca en git** en texto plano
- Deployment reproducible sin intervención manual
- Recuperación de emergencia sin dependencias de nube externa
- Rotación de credenciales sin redesplegar contenedores

---

## 2. Candidatos Evaluados

### 2.1 Doppler.com

Servicio SaaS que actúa como fuente de verdad centralizada para secretos, con CLI, SDKs y webhooks.

**Flujo operativo:**
```
Doppler Dashboard → doppler run -- docker-compose up
                 → doppler secrets download --format env > .env
                 → doppler CLI inyecta vars al proceso
```

**Ventajas:**
- UI web para gestión y auditoría
- Historial de cambios con autoría
- Rotación automática con webhooks
- Integración nativa con GitHub Actions, Docker, Kubernetes
- Permisos granulares por proyecto/entorno (dev/staging/prod)
- CLI única: `doppler run -- <comando>`

**Desventajas:**
- Dependencia de nube externa: si Doppler cae, el pipeline no arranca
- Free tier limitado a 3 proyectos y 1 usuario
- `doppler run` añade ~200ms de latencia por llamada al API en cada `docker-compose up`
- Requiere `DOPPLER_TOKEN` en servidor (secreto para gestionar secretos → problema de bootstrap)
- Vendor lock-in: migrar fuera requiere exportar y reformatear

**Precio:** Free (1 usuario, 3 proyectos), Team $6.99/usuario/mes

---

### 2.2 .env encriptado con sops + age

`sops` (Secrets OPerationS, Mozilla) encripta archivos de configuración con claves simétricas (`age`) o asimétricas (PGP, AWS KMS).

`age` es un esquema moderno de encriptación de archivos: una línea para generar la clave, una para encriptar, una para desencriptar.

**Flujo operativo:**
```
age-keygen → age.key (local + backup seguro)
sops --encrypt .env > .env.enc    # encriptar
git add .env.enc                   # seguro commitear
sops --decrypt .env.enc > .env    # en servidor, antes de docker-compose
```

**Ventajas:**
- **Sin dependencias externas**: pipeline funciona sin internet
- Git-native: `.env.enc` commiteable y auditable por diff
- `sops` edita in-place (`sops edit .env.enc` abre editor con valores desencriptados)
- Múltiples backends de clave: `age` local, AWS KMS, GCP KMS, PGP
- Docker Compose lo consume directamente vía `--env-file`
- Un solo binario (`sops` + `age`) sin cuentas, sin tokens de terceros
- Rotación: cambiar clave `age`, re-encriptar, commitear → propagación instantánea

**Desventajas:**
- No tiene UI web ni auditoría integrada
- Backups de `age.key` son responsabilidad del operador
- Sin acceso remoto al valor: hay que SSH al servidor para verificar
- Diff en git muestra metadata (clave pública, versión sops) pero no valores
- Onboarding de nuevos colaboradores requiere compartir la clave `age` por canal seguro

**Precio:** Gratuito y open-source

---

### 2.3 Otras alternativas consideradas y descartadas

| Herramienta | Razón de descarte |
|-------------|------------------|
| `git-crypt` | Encripta archivos enteros; diff inútil; difícil rotar clave |
| `transcrypt` | Similar a git-crypt; menos mantenido |
| `ansible-vault` | Require Ansible como dependencia pesada |
| HashiCorp Vault | Overkill para VPS de un solo nodo; gestión compleja |
| AWS Secrets Manager | Coste ~$0.40/secreto/mes + dependencia AWS |
| 1Password CLI | Excelente pero $4/mes y vendor lock-in |

---

## 3. Tabla Comparativa

| Criterio | Doppler | sops + age | Peso |
|----------|---------|------------|------|
| Sin dependencia externa en producción | ❌ | ✅ | Alto |
| Git-native (diff legible) | Parcial | ✅ | Medio |
| UI de auditoría / historial | ✅ | ❌ (git log) | Bajo |
| Rotación de secretos | ✅ webhooks | Manual (script) | Medio |
| Bootstrap sin secreto previo | ❌ (necesita DOPPLER_TOKEN) | ✅ (age.key en servidor) | Alto |
| Coste para 1 usuario | Free | Free | — |
| Complejidad de setup inicial | Baja | Media | Medio |
| Recuperación offline | ❌ | ✅ | Alto |
| Integración Docker Compose | Nativa | `sops decrypt + --env-file` | Medio |
| Portabilidad (sin vendor lock-in) | Media | Alta | Medio |

---

## 4. Recomendación para Agartha VPS

**Elegir: sops + age**

**Justificación:**

El pipeline de Agartha opera en modo `radar` (cron nocturno) y depende de que el entorno de producción esté operativo de forma autónoma. Una dependencia de Doppler introduce un punto de fallo externo donde Doppler caído = pipeline caído = ninguna oportunidad de arbitraje procesada. Con `sops + age`, el servidor tiene todo lo necesario en local.

El argumento del bootstrap también es decisivo: Doppler requiere un `DOPPLER_TOKEN` en el servidor para que el CLI funcione — un secreto para gestionar secretos. Con `age.key`, el único secreto bootstrap es la clave age almacenada en el sistema de archivos del VPS, que ya es el equivalente de "tener acceso al servidor".

Doppler tiene sentido para equipos de 5+ personas donde la auditoría y el control de acceso granular justifican el SaaS. Para un operador único en un VPS dedicado, `sops + age` es más simple en el estado estacionario.

---

## 5. Setup: sops + age en Agartha

### 5.1 Instalación en máquina local (Windows/WSL) y VPS (Ubuntu 22.04)

```bash
# age — en Ubuntu/Debian
sudo apt-get install age

# sops — descargar binario
wget https://github.com/getsops/sops/releases/latest/download/sops-v3.9.0.linux.amd64 \
  -O /usr/local/bin/sops && chmod +x /usr/local/bin/sops

# Verificar
sops --version
age --version
```

En Windows (local, via WinGet o Chocolatey):
```powershell
winget install FiloSottile.age
winget install Mozilla.sops
```

### 5.2 Generar clave age

```bash
# Genera par de claves; guardar AMBAS líneas
age-keygen -o ~/.config/agartha/age.key
# Salida:
# Public key: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# (Private key en el archivo)

# Ver la clave pública (para .sops.yaml)
age-keygen -y ~/.config/agartha/age.key
```

**Backup obligatorio**: copiar `age.key` a un gestor de contraseñas personal (Bitwarden, 1Password) o imprimirla y guardarla fuera de línea. Sin esta clave, los secretos son irrecuperables.

### 5.3 Configurar .sops.yaml en la raíz del proyecto

```yaml
# .sops.yaml — define qué archivos encripta sops y con qué clave
creation_rules:
  - path_regex: \.env\.enc$
    age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  - path_regex: \.env\.prod\.enc$
    age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Reemplazar `age1xxx...` con la clave pública generada en 5.2.

### 5.4 Encriptar el .env existente

```bash
# Primera vez: encriptar
sops --encrypt .env > .env.enc

# Verificar que está encriptado (debe mostrar ENC[AES256_GCM,...])
head -5 .env.enc

# Añadir a git (es seguro)
git add .env.enc .sops.yaml
git commit -m "chore: add encrypted env file"

# Añadir .env a .gitignore si no está ya
echo ".env" >> .gitignore
echo "age.key" >> .gitignore
```

### 5.5 Editar secretos (flujo diario)

```bash
# Editar in-place: sops desencripta, abre $EDITOR, re-encripta al guardar
SOPS_AGE_KEY_FILE=~/.config/agartha/age.key sops edit .env.enc

# Alternativa: desencriptar temporalmente para inspección
SOPS_AGE_KEY_FILE=~/.config/agartha/age.key sops decrypt .env.enc > .env.tmp
# ... inspeccionar .env.tmp ...
rm .env.tmp
```

### 5.6 Deploy en VPS

```bash
# En el servidor: copiar age.key una vez (durante el setup inicial del VPS)
scp ~/.config/agartha/age.key deploy@vps:/home/deploy/.config/agartha/age.key
chmod 600 /home/deploy/.config/agartha/age.key

# En el servidor: script de deploy (incluir en setup_vps.sh o CD pipeline)
export SOPS_AGE_KEY_FILE=/home/deploy/.config/agartha/age.key

# Desencriptar antes de docker-compose
sops --decrypt .env.enc > .env

# Lanzar servicios
docker-compose --env-file .env up -d

# Limpiar .env en texto plano post-arranque (opcional, si los contenedores ya tienen las vars)
rm .env
```

### 5.7 Integración con GitHub Actions (CI/CD)

```yaml
# .github/workflows/deploy.yml — fragmento relevante
- name: Setup age key
  run: |
    mkdir -p ~/.config/agartha
    echo "${{ secrets.AGE_PRIVATE_KEY }}" > ~/.config/agartha/age.key
    chmod 600 ~/.config/agartha/age.key

- name: Decrypt env
  run: |
    export SOPS_AGE_KEY_FILE=~/.config/agartha/age.key
    sops --decrypt .env.enc > .env
```

El secreto `AGE_PRIVATE_KEY` (el contenido completo de `age.key`) se registra una sola vez en GitHub Actions → Settings → Secrets.

---

## 6. Rotación de Secretos

### 6.1 Rotar un valor individual (ej: nueva Stripe key)

```bash
SOPS_AGE_KEY_FILE=~/.config/agartha/age.key sops edit .env.enc
# Editar STRIPE_SECRET_KEY=sk_live_nueva_clave
# Guardar → sops re-encripta automáticamente
git add .env.enc && git commit -m "chore: rotate stripe key"
git push
# En VPS: git pull → re-deploy
```

### 6.2 Rotar la clave age completa (máxima seguridad)

```bash
# 1. Generar nueva clave
age-keygen -o ~/.config/agartha/age_new.key
NEW_PUBLIC=$(age-keygen -y ~/.config/agartha/age_new.key)

# 2. Actualizar .sops.yaml con la nueva clave pública
# 3. Re-encriptar todos los archivos
SOPS_AGE_KEY_FILE=~/.config/agartha/age.key sops updatekeys .env.enc
# sops re-encripta con la nueva clave listada en .sops.yaml

# 4. Reemplazar age.key por age_new.key
mv ~/.config/agartha/age_new.key ~/.config/agartha/age.key

# 5. Actualizar en VPS y GitHub Actions
scp ~/.config/agartha/age.key deploy@vps:/home/deploy/.config/agartha/age.key
# Actualizar secret AGE_PRIVATE_KEY en GitHub
```

---

## 7. Estructura de Archivos

```
Agartha/
├── .env                  # NUNCA en git — archivo local de trabajo
├── .env.enc              # ✅ en git — encriptado con sops+age
├── .env.example          # ✅ en git — template sin valores reales
├── .sops.yaml            # ✅ en git — reglas de encriptación
└── .gitignore            # incluye .env y age.key

~/.config/agartha/
└── age.key               # NUNCA en git — clave privada age
```

---

## 8. Checklist de Setup Inicial (VPS)

- [ ] Instalar `age` y `sops` en VPS y máquina local
- [ ] Generar `age.key` local con `age-keygen`
- [ ] Crear `.sops.yaml` con clave pública
- [ ] Encriptar `.env` → `.env.enc` con `sops --encrypt`
- [ ] Commit y push de `.env.enc` y `.sops.yaml`
- [ ] Verificar `.env` en `.gitignore`
- [ ] Hacer backup de `age.key` en gestor de contraseñas
- [ ] Copiar `age.key` al VPS vía `scp`
- [ ] Añadir `AGE_PRIVATE_KEY` como secret en GitHub Actions
- [ ] Verificar desencriptación en VPS: `sops --decrypt .env.enc | head -3`

---

## 9. Recuperación de Emergencia

**Escenario A: age.key perdida localmente**
→ Recuperar del backup en gestor de contraseñas. Recolocar en `~/.config/agartha/age.key`.

**Escenario B: age.key perdida en VPS**
→ Copiar desde máquina local: `scp ~/.config/agartha/age.key deploy@vps:/home/deploy/.config/agartha/`

**Escenario C: age.key perdida en ambos lugares + backup**
→ Los secretos en `.env.enc` son **irrecuperables**. Regenerar TODOS los secretos desde las plataformas origen (Stripe dashboard, Telegram BotFather, Google Cloud Console, etc.) y re-encriptar con nueva clave.
→ Lección: siempre guardar backup en gestor de contraseñas offline.

**Escenario D: VPS comprometido**
→ Revocar la clave `age` actual rotando a una nueva (sección 6.2). Invalidar TODOS los tokens/API keys expuestos desde sus respectivas plataformas. Re-deploy desde cero.

---

## 10. find-skills Results (2026-05-08)

Queries ejecutadas antes de la decisión de herramientas:

| Query | Mejor resultado | Installs | Decisión |
|-------|----------------|----------|---------|
| `secrets management env encryption` | `patricio0312rev/skills@env-secrets-manager` | 110 | No instalar — bajo installs |
| `doppler sops devops secrets VPS` | `terrylica/cc-skills@doppler-secret-validation` | 92 | No instalar — bajo installs |

Umbral de confianza: 1K+ installs. Ningún skill encontrado supera el umbral. Se procede con `sops + age` basándose en conocimiento directo.
