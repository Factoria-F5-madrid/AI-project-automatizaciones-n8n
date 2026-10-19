# 👟 Proyecto: Automatizaciones con n8n · Zapatería Paso Firme

<img width="11520" height="3456" alt="n8n" src="https://github.com/user-attachments/assets/f8bdfbe6-0400-4f8e-a011-efb25c188db4" />

## 📋 Planteamiento

**Zapatería Paso Firme** es una tienda de barrio con una sola dependienta y su dueña, Marisa. Además de la venta normal, su servicio estrella es el **sistema de apartados**: el cliente elige unos zapatos, deja un abono inicial y los va pagando poco a poco hasta llevárselos.

Hoy todo se lleva **a mano**: una libreta para los apartados y un Excel donde Marisa apunta las ventas del día y, a final de mes, suma lo recaudado y lo que le queda por cobrar. Los problemas se repiten cada semana:

- Hay que buscar en la libreta cuánto ha pagado un cliente y cuánto le falta, y a veces las cuentas no cuadran.
- Nadie avisa a los clientes de que su plazo está a punto de vencer, así que hay apartados olvidados con zapatos ocupando el almacén.
- El cierre de caja diario y la suma mensual se hacen con calculadora, tarde y con errores.
- Marisa no sabe en ningún momento cuánto dinero tiene pendiente de cobrar.
- Cada vez más clientes pagan sus abonos desde casa por **Bizum o transferencia**. Marisa tiene que revisar los avisos del banco, adivinar de qué apartado es cada pago y apuntarlo a mano; algunos se le pasan.

Marisa ya ha dado el primer paso: una app sencilla donde la dependienta registra apartados, abonos y ventas. Vuestra pareja ha sido contratada para **automatizar todo lo demás con n8n**: lo que hoy se hace con libreta, calculadora y memoria debe ocurrir solo.

Como en la mayoría de equipos actuales, **el trabajo se hará con agentes de IA**: un agente (como [OpenCode](https://opencode.ai)) con modelos gratuitos ayuda a diseñar, generar y depurar los flujos, y vosotros hacéis de *tech lead*: definís qué automatizar, dais contexto al agente, revisáis lo que genera y decidís qué se pone en producción. El agente propone, pero la responsabilidad de los flujos es vuestra.

**Modalidad:** por parejas.

## 📏 Reglas del negocio: sistema de apartado

| Regla | Detalle |
|---|---|
| Abono inicial | Mínimo **5 €** en el momento de apartar |
| Plazo | Máximo **3 meses** (90 días) desde la fecha del apartado para pagar el total |
| Abonos | Se pueden hacer los abonos que se quieran, de cualquier importe, sin superar lo que falta por pagar |
| Liquidación | Cuando lo que falta llega a 0 €, el apartado queda **liquidado** y el cliente puede recoger sus zapatos |
| Vencimiento | Si pasan los 3 meses sin liquidar, el apartado queda **vencido**: los zapatos vuelven a la venta y lo abonado se convierte en un **vale de compra** para el cliente (no se devuelve en efectivo) |
| Un apartado = un par | Cada apartado corresponde a un solo producto (modelo + talla) |

Y las cifras que Marisa necesita:

- **Ventas del día:** ventas directas + abonos cobrados ese día (los abonos iniciales también cuentan).
- **Recaudación mensual:** la suma de todo lo cobrado en el mes, separando ventas directas y abonos de apartados.
- **Total pendiente de cobro:** la suma de lo que falta por pagar en todos los apartados activos.

## 🗂️ Datos de partida

En [`data/`](data/) tenéis una muestra del Excel actual de la tienda, tal y como lo lleva Marisa:

- [`excel_actual_apartados.csv`](data/excel_actual_apartados.csv): apartados y abonos mezclados en la misma hoja.
- [`excel_actual_ventas.csv`](data/excel_actual_ventas.csv): ventas del día y el total mensual sumado a mano.

Son datos **reales del día a día**, con lo que eso implica: fechas en distintos formatos, nombres escritos de varias maneras, importes con el símbolo €, teléfonos que faltan, un abono inicial por debajo del mínimo y totales calculados a mano. Sirven para el flujo de **migración** (nivel medio): limpiarlos y cargarlos en la app por API.

En [`data/correos/`](data/correos/) tenéis **avisos del banco** como los que recibe Marisa cuando un cliente paga por Bizum o transferencia. Sirven para el flujo de **abonos a distancia** (nivel esencial) y están pensados para los apartados de ejemplo de la app. Hay casos fáciles y casos trampa:

| Correo | Qué tiene que pasar |
|---|---|
| `01_bizum_carmen`, `09_bizum_silvia` | El nombre coincide con un único apartado activo: se registra el abono |
| `02_bizum_jorge` | El ordenante está abreviado, pero el concepto trae el nº de apartado |
| `03_transferencia_lucia` | Paga justo lo que falta: el apartado queda **liquidado** |
| `04_bizum_laura` | Paga **más** de lo pendiente: la app lo rechaza y hay que avisar a Marisa |
| `05_bizum_romero` | Solo apellido e inicial y sin concepto: hay que preguntar a Marisa antes de registrar nada |
| `06_bizum_paula` | El apartado está **fuera de plazo**: no se puede abonar, hay que avisar a Marisa |
| `07_transferencia_desconocido` | No coincide con ningún cliente: preguntar a Marisa |
| `08_publicidad_banco` | No es un pago: se ignora |

Para probarlos, enviad estos correos (asunto y cuerpo) a la cuenta que lea n8n. Mientras desarrolláis, también podéis pegar el texto en un formulario de n8n (Form Trigger) para no depender del correo.

## 🚀 Cómo empezar

Necesitáis [Git](https://git-scm.com/) y [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalados y abiertos.

**1. Una persona de la pareja clona el proyecto:**

```bash
git clone https://github.com/Factoria-F5-madrid/AI-project-automatizaciones-n8n.git paso-firme
cd paso-firme
```

**2. Cortad la conexión con este repositorio.** El proyecto es vuestro: no se trabaja sobre el repositorio de Factoría F5, así que hay que quitarle el remoto `origin`:

```bash
git remote remove origin
```

**3. Conectadlo a vuestro propio repositorio.** Cread en GitHub un repositorio **vacío** (sin README, sin `.gitignore` y sin licencia) y enlazadlo:

```bash
git remote add origin https://github.com/<vuestro-usuario>/<vuestro-repo>.git
git push -u origin main
```

Si usáis GitHub CLI, los pasos de crear y enlazar se hacen en uno: `gh repo create <vuestro-repo> --private --source . --push`.

**4. Invitad a vuestra pareja** como colaboradora del repositorio (*Settings → Collaborators*). Ella lo clona desde **vuestro** repositorio, no desde este.

**5. A partir de aquí, todo se sube a vuestro repositorio** con el flujo de siempre (rama, commit, push y Pull Request):

```bash
git switch -c flujo-confirmacion-apartado
git add .
git commit -m "Añade flujo de confirmación de apartado"
git push -u origin flujo-confirmacion-apartado
```

Comprobad en cualquier momento a dónde apunta vuestro proyecto con `git remote -v`: tiene que salir vuestro repositorio, no el de Factoría F5.

> **¿Y si el profe actualiza el enunciado o la app?** Podéis traer los cambios sin volver a conectaros: `git pull https://github.com/Factoria-F5-madrid/AI-project-automatizaciones-n8n.git main`

**6. Levantad la app y n8n:**

```bash
cp .env.example .env
docker compose up -d
```

Cambiad `API_KEY` en el `.env` por una clave vuestra (el `.env` no se sube a GitHub). Después abrid http://localhost:8000 (la tienda) y http://localhost:5678 (n8n; la primera vez os pedirá crear una cuenta local).

Para pararlo todo: `docker compose down`. Para borrar también los datos y empezar de cero: `docker compose down -v`.

## 🏪 El software de la tienda

Para no empezar de cero, la tienda ya tiene una **aplicación básica** en [`app/`](app/) que sustituye a la libreta. Vuestro trabajo **no es programarla**, sino **automatizar todo lo que pasa alrededor** con n8n. Cuando la levantéis (ver [Cómo empezar](#-cómo-empezar)) tendréis:

| Servicio | URL | Para qué |
|---|---|---|
| App de la tienda | http://localhost:8000 | Registrar apartados, abonos y ventas, y descargar todo en **Excel** |
| Documentación de la API | http://localhost:8000/docs | Probar los endpoints que usará n8n (Swagger) |
| n8n | http://localhost:5678 | Construir las automatizaciones |

**Qué hace ya la app:**

- Guarda los datos (SQLite) y **aplica las reglas del apartado**: abono inicial mínimo, plazo de 90 días, no pagar de más y liquidación automática.
- Pantallas para la dependienta: lista de apartados con buscador, filtros por estado y paginación, alta de apartados, ficha de cada apartado con sus abonos y ventas directas.
- Botón **Descargar Excel** con una hoja por tabla (Apartados, Abonos, Ventas, Vales), para que Marisa siga teniendo "su Excel".

**Cómo se conecta con n8n:**

- **La app avisa a n8n (webhook):** cada vez que pasa algo, la app envía un `POST` a `N8N_WEBHOOK_URL` (por defecto `http://n8n:5678/webhook/tienda`) con este formato:

  ```json
  { "evento": "abono.registrado", "datos": { "id": 1, "cliente": "Carmen Ruiz", "pendiente": 59.9, "estado": "activo", ... } }
  ```

  | Evento | Cuándo |
  |---|---|
  | `apartado.creado` | Se registra un apartado nuevo |
  | `abono.registrado` | Se registra un abono (si `estado` es `liquidado`, ya está pagado) |
  | `venta.registrada` | Se registra una venta directa |
  | `apartado.vencido` | Se marca un apartado como vencido y se genera su vale |

- **n8n consulta y actúa en la app (API REST):** desde n8n, con el nodo HTTP Request y la URL `http://tienda:8000/api/...`, enviando la cabecera `X-API-Key` con el valor de `API_KEY` del `.env`.

  | Endpoint | Para qué |
  |---|---|
  | `GET /api/apartados?estado=activo` | Apartados (con lo abonado, lo pendiente y la fecha límite) |
  | `GET /api/apartados/{id}` | Un apartado con todos sus abonos |
  | `POST /api/apartados` | Crear un apartado (acepta `fecha` para migrar datos antiguos) |
  | `POST /api/apartados/{id}/abonos` | Registrar un abono |
  | `POST /api/apartados/{id}/vencer` | Marcar como vencido un apartado fuera de plazo y generar su vale |
  | `GET /api/abonos?desde=&hasta=` | Abonos entre dos fechas |
  | `GET /api/ventas?desde=&hasta=` | Ventas entre dos fechas |
  | `POST /api/ventas` | Registrar una venta |
  | `GET /api/vales` | Vales de compra generados |

**Datos de ejemplo:** la primera vez que arranca, la app se llena sola con unos meses de actividad de la tienda (24 apartados y unas 250 ventas), con fechas relativas al día en que la levantéis. Así siempre hay:

- apartados que vencen **dentro de 7 días** y **mañana** (para los recordatorios),
- apartados **fuera de plazo** que siguen activos (para que vuestro flujo los venza),
- apartados liquidados, uno ya vencido con su vale, y ventas y abonos de **hoy** y de los **meses anteriores** (para el cierre diario y el informe mensual).

Los clientes de ejemplo tienen correos `@example.com`: para recibir vosotros los mensajes, cread un apartado nuevo con vuestro correo. Para empezar de cero, `docker compose down -v` borra los datos, y con `SEED=0` en el `.env` la app arranca vacía.

**Lo que la app NO hace (y os toca a vosotros con n8n):** avisar a los clientes, recordar vencimientos, vencer los apartados fuera de plazo, hacer cierres de caja, calcular la recaudación mensual y el total pendiente, enviar informes y migrar el Excel antiguo.

## 🎯 Objetivo

Conectar la app de la tienda con un conjunto de **flujos de n8n** que avisen a los clientes, controlen los vencimientos y den a Marisa sus cifras diarias y mensuales sin hacer una sola suma.

## 🛠️ Requisitos Técnicos

1. **App de la tienda y n8n** con **Docker** (el `docker-compose.yml` ya está incluido)
2. Integración con la **app de la tienda** mediante el **Webhook** de eventos y su **API REST** (nodo HTTP Request)
3. Google Sheets u otra herramienta similar solo para lo que la app no guarda (por ejemplo, el histórico de cierres de caja)
4. Al menos un flujo programado (**Schedule Trigger**)
5. Notificaciones a clientes y a la tienda (Gmail, Telegram, Slack…)
6. Gestión segura de **credenciales** en n8n, **nunca escritas en los nodos ni subidas al repositorio**
7. Validación de las reglas del negocio dentro de los flujos (IF / Switch y nodo **Code** cuando sea necesario)
8. Manejo de errores (reintentos, ramas de error y un **Error Workflow**)
9. Flujos exportados en **JSON** y versionados en Git y GitHub
10. Desarrollo asistido por **agentes de IA** con modelos gratuitos (ver sección siguiente)

## 🔄 Automatizaciones a construir

| # | Flujo | Disparador | Qué hace |
|---|---|---|---|
| 1 | **Confirmación de apartado** | Evento `apartado.creado` | Envía al cliente un resumen: qué ha apartado, cuánto ha pagado, cuánto le falta y hasta cuándo |
| 2 | **Recibo de abono** | Evento `abono.registrado` | Envía el recibo del abono con lo que falta. Si el apartado queda liquidado, avisa de que puede recoger sus zapatos |
| 3 | **Abonos a distancia** | Correo nuevo (Gmail o IMAP) | Lee los avisos del banco, descarta los que no son pagos, usa **IA** para sacar ordenante, importe y concepto, busca el apartado por API y registra el abono. Si no está claro de quién es, si paga de más o si el apartado está fuera de plazo, **no registra nada** y pregunta a Marisa (correo o Telegram) |
| 4 | **Venta grande** | Evento `venta.registrada` | Avisa a Marisa de las ventas por encima de un importe que ella decida |
| 5 | **Cierre diario** | Programado (cada noche) | Pide a la API las ventas y abonos del día, suma por forma de pago, guarda el cierre y envía el resumen a Marisa |
| 6 | **Recordatorios y vencimientos** | Programado (cada mañana) | Avisa a los clientes cuyo plazo vence en 7 días y en 1 día; vence por API los que han pasado el plazo (la app genera el vale) y avisa a la tienda para devolver los zapatos a la venta |
| 7 | **Informe mensual** | Programado (día 1 de cada mes) | Recaudación del mes (ventas + abonos), total pendiente de cobro, apartados nuevos, liquidados y vencidos, enviado por correo a Marisa |
| 8 | **Error Workflow** | Error en cualquier flujo | Avisa a la tienda con el flujo, el paso y el error |

## 🤖 Desarrollo Agéntico con IA

El proyecto debe desarrollarse con un agente de IA en la terminal, trabajando como se hace hoy en la industria.

**Herramientas**

- Agente: **[OpenCode](https://opencode.ai)** (recomendado). Se pueden usar alternativas abiertas o gratuitas (Aider, Cline, Kilo Code…), pero hay que justificar la elección.
- Modelos **gratuitos**, por ejemplo: los modelos gratuitos de OpenCode Zen, modelos `:free` de OpenRouter, la capa gratuita de Groq o Gemini. Los mismos modelos se pueden usar dentro de n8n en los nodos de IA.
- **[n8n-mcp](https://github.com/czlonkowski/n8n-mcp)** (recomendado): servidor MCP que da al agente la documentación de todos los nodos de n8n y, conectado a la API de vuestra instancia, le permite crear, validar y actualizar flujos.
- Si tienen IAs de pago pueden utilizarlas, solo que tenerlo en cuenta para no pisar el trabajo del equipo, delimitar muy bien el alcance que tendrán.

**¿En qué ayuda el agente si n8n es visual?**

Un flujo de n8n es un archivo JSON y n8n tiene una API REST, así que un agente puede trabajar con ellos igual que con código:

- **Generar y modificar flujos:** a partir de una spec, el agente crea el JSON del flujo y lo sube a n8n (vía MCP o la API). El equipo lo abre en el editor, lo prueba y lo ajusta.
- **Elegir y configurar nodos:** consulta qué nodo usar y qué parámetros necesita, en lugar de buscarlo a mano en la documentación.
- **Escribir el código de los nodos Code** y las expresiones complejas (`{{ $json... }}`) de transformación de datos.
- **Depurar:** se le pasa el error de una ejecución fallida y el JSON del flujo, y propone la corrección.
- **Pruebas:** payloads de prueba para los webhooks y scripts para exportar e importar flujos.
- **Documentar:** genera la documentación de cada flujo a partir de su JSON.

El editor visual sigue siendo donde se prueba y se revisa: el agente no sustituye abrir el flujo y ejecutarlo.

**Forma de trabajo**

1. **Contexto antes que flujos:** crear un `AGENTS.md` en la raíz con el negocio y sus reglas del apartado, los servicios integrados, las convenciones de nombres de flujos y nodos, cómo importar y exportar flujos y lo que el agente **no** debe hacer (por ejemplo: no escribir credenciales en el JSON, no activar flujos en producción).
2. **SDD & Ontologías:** antes de pedirle nada al agente, cada automatización se define con *Spec-Driven Development* en una spec (`specs/`) con el disparador, las entradas, las salidas, los casos de error y los criterios de aceptación, apoyada en una ontología del dominio: entidades del negocio (`Cliente`, `Producto`, `Apartado`, `Abono`, `Venta`, `CierreDiario`…), sus atributos, relaciones y reglas. Así el agente y el equipo comparten el mismo vocabulario y no inventan conceptos.
3. **Tareas pequeñas:** en pareja, repartid los flujos para no pisaros; una tarea del Kanban equivale a un flujo (o parte de uno), una rama y una Pull Request con el JSON exportado.
4. **Revisión humana obligatoria:** todo flujo generado se importa, se prueba con datos de ejemplo y se revisa en la PR antes de mergear. Hay que prestar especial atención a la seguridad: credenciales, datos personales y webhooks expuestos.
5. **Pruebas como contrato:** cada flujo tiene datos de prueba (pinned data o payloads de ejemplo) y un resultado esperado. Si una prueba falla, se arregla el flujo, no se cambia la prueba.
6. **Trazabilidad:** registrar los prompts más relevantes y las decisiones que se tomaron (qué se aceptó, qué se rechazó y por qué).

## 📦 Entregables

1. Mapa del proceso de apartado: cómo se hace hoy y cómo queda automatizado (diagrama BPMN, Miro, Excalidraw o similar)
2. Vuestro propio repositorio (ver [Cómo empezar](#-cómo-empezar)) con los flujos exportados en JSON (carpeta `workflows/`) y README con instrucciones para importarlos y configurarlos
3. Lista de credenciales y variables que necesita cada flujo (sin los valores)
4. Un **flujo de prueba** o script que cree datos de ejemplo en la app por API para poder hacer la demo
5. Datos de prueba y evidencias de ejecución (capturas o vídeo de un apartado completo: alta, abonos, liquidación)
6. Tablero Kanban con historias de usuario (por ejemplo: *"Como dependienta quiero registrar un abono en menos de 30 segundos para no hacer esperar al cliente"*)
7. `AGENTS.md` y carpeta `specs/` con las especificaciones de cada automatización
8. **Bitácora de IA** (`docs/ai-log.md`): herramienta y modelos usados, prompts clave, errores o alucinaciones del agente y cómo se corrigieron
9. Historial de PRs con revisiones visibles de los flujos generados
10. Breve retrospectiva de la pareja

## 🏆 Niveles de Entrega

### 🟢 Nivel Esencial

- App y n8n levantados con `docker compose` y conectados (los eventos de la app llegan a n8n)
- Flujos **1 (Confirmación de apartado)**, **2 (Recibo de abono)**, **3 (Abonos a distancia)** y **5 (Cierre diario)** funcionando
- El flujo 3 resuelve bien los 8 correos de `data/correos/`: la IA solo extrae los datos, y las decisiones (qué apartado es, si se puede registrar) las toma el flujo con la API
- Un único webhook que reparta los eventos con un nodo **Switch** según el campo `evento`
- Mensajes al cliente por correo o Telegram con los importes correctos (los da la app, no se recalculan a mano)
- **Error Workflow** que avise a la tienda
- Credenciales gestionadas en n8n y flujos exportados en JSON en GitHub
- `AGENTS.md` funcional y bitácora de IA con al menos los prompts de cada flujo principal

### 🟡 Nivel Medio

- Flujos **4 (Venta grande)**, **6 (Recordatorios y vencimientos)** y **7 (Informe mensual)**
- Aviso al cliente cuando su apartado vence, con el código y el importe de su vale
- Sub-workflows reutilizables (**Execute Workflow**), por ejemplo "buscar apartado" o "enviar notificación"
- **Migración del Excel actual**: flujo que lea los CSV de `data/`, limpie los datos (fechas, nombres, importes), cree los apartados y abonos en la app por API (con su `fecha` original) y deje en un informe los casos dudosos
- Informe mensual en PDF o con tabla en el correo
- Comparativa de al menos 2 modelos gratuitos en una misma tarea (calidad, velocidad, errores)

### 🟠 Nivel Avanzado

- **Asistente de IA por Telegram** (nodo AI Agent con un modelo gratuito y la API de la tienda como herramienta):
  - el cliente pregunta *"¿cuánto me falta?"* y recibe su saldo y fecha límite
  - Marisa pregunta *"¿cuánto se recaudó esta semana?"* o *"¿qué apartados vencen este mes?"*
- **Otras entradas de datos automáticas** (al menos una):
  - **Apartados desde casa:** formulario de n8n o bot de Telegram donde el cliente pide apartar unos zapatos; n8n crea una solicitud, avisa a la tienda y el apartado se confirma cuando llega el abono inicial
  - **Ventas del datáfono:** cada noche n8n importa el CSV de cobros con tarjeta y los registra como ventas, sin duplicar las que ya estén
- Mensajes de recordatorio redactados por IA con un tono cercano, siempre con los importes calculados por el flujo (nunca por el modelo)
- Webhook de n8n protegido (autenticación por cabecera) y validación de los datos que llegan
- Datos personales conforme al RGPD: solo los datos necesarios, consentimiento para recibir mensajes y no enviar a modelos externos más datos de los imprescindibles
- Comandos, skills o subagentes personalizados en OpenCode para tareas repetitivas (generar specs, revisar flujos…)

### 🔴 Nivel Experto

- Panel sencillo para Marisa (Looker Studio, una web o similar) con ventas, recaudación, pendiente de cobro y apartados por vencer
- n8n con PostgreSQL en `docker-compose`, con copias de seguridad automáticas
- Despliegue en la nube (Render, Railway, un VPS, Google Cloud, etc.) con HTTPS
- Pipeline de CI con GitHub Actions que valide los JSON de los flujos en cada PR
- Exponer los flujos como servidor MCP (**MCP Server Trigger**) para que otros agentes consulten el estado de los apartados
