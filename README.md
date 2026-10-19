# 👟 Proyecto: Automatizaciones con n8n · Zapatería Paso Firme

![Banner Proyectos](https://github.com/user-attachments/assets/94ecebe4-ceba-47ae-8f3c-af14bdfe8606)

## 📋 Planteamiento

**Zapatería Paso Firme** es una tienda de barrio con una sola dependienta y su dueña, Marisa. Además de la venta normal, su servicio estrella es el **sistema de apartados**: el cliente elige unos zapatos, deja un abono inicial y los va pagando poco a poco hasta llevárselos.

Hoy todo se lleva **a mano**: una libreta para los apartados y un Excel donde Marisa apunta las ventas del día y, a final de mes, suma lo recaudado y lo que le queda por cobrar. Los problemas se repiten cada semana:

- Hay que buscar en la libreta cuánto ha pagado un cliente y cuánto le falta, y a veces las cuentas no cuadran.
- Nadie avisa a los clientes de que su plazo está a punto de vencer, así que hay apartados olvidados con zapatos ocupando el almacén.
- El cierre de caja diario y la suma mensual se hacen con calculadora, tarde y con errores.
- Marisa no sabe en ningún momento cuánto dinero tiene pendiente de cobrar.

Vuestra pareja ha sido contratada para **automatizar este proceso con n8n** sin cambiar la forma de trabajar de la tienda: la dependienta debe poder registrar apartados, abonos y ventas desde el móvil o el ordenador en segundos, y el resto debe ocurrir solo.

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

Son datos **reales del día a día**, con lo que eso implica: fechas en distintos formatos, nombres escritos de varias maneras, importes con el símbolo €, teléfonos que faltan, un abono inicial por debajo del mínimo y totales calculados a mano. Parte del trabajo es diseñar una estructura limpia para los datos y decidir qué hacer con estos casos.

## 🎯 Objetivo

Sustituir la libreta y las cuentas a mano por un conjunto de **flujos de n8n** que registren apartados, abonos y ventas, apliquen las reglas del negocio, avisen a los clientes y den a Marisa sus cifras diarias y mensuales sin hacer una sola suma.

## 🛠️ Requisitos Técnicos

1. **n8n** autoalojado con **Docker** (`docker-compose`)
2. **Google Sheets** como sustituto del Excel, con una hoja por entidad (Clientes, Apartados, Abonos, Ventas, Cierres)
3. Registro de datos mediante **formularios de n8n** (Form Trigger) o Webhook
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
| 1 | **Nuevo apartado** | Formulario | Valida abono ≥ 5 € y precio, calcula lo que falta y la fecha límite, guarda el apartado y envía al cliente un resumen (qué ha apartado, cuánto ha pagado, cuánto le falta y hasta cuándo) |
| 2 | **Registrar abono** | Formulario | Busca el apartado, comprueba que no esté vencido ni se pague de más, actualiza lo que falta y envía un recibo. Si llega a 0 €, lo marca como liquidado y avisa de que puede recoger sus zapatos |
| 3 | **Venta directa** | Formulario | Registra una venta normal (producto, importe, forma de pago) |
| 4 | **Cierre diario** | Programado (cada noche) | Suma ventas y abonos del día por forma de pago, lo guarda en la hoja de cierres y envía el resumen a Marisa |
| 5 | **Recordatorios y vencimientos** | Programado (cada mañana) | Avisa a los clientes cuyo plazo vence en 7 días y en 1 día; marca como vencidos los que han pasado el plazo, genera el vale y avisa a la tienda para devolver los zapatos a la venta |
| 6 | **Informe mensual** | Programado (día 1 de cada mes) | Recaudación del mes (ventas + abonos), total pendiente de cobro, apartados nuevos, liquidados y vencidos, enviado por correo a Marisa |
| 7 | **Error Workflow** | Error en cualquier flujo | Avisa a la tienda con el flujo, el paso y el error |

## 🤖 Desarrollo Agéntico con IA

El proyecto debe desarrollarse con un agente de IA en la terminal, trabajando como se hace hoy en la industria.

**Herramientas**

- Agente: **[OpenCode](https://opencode.ai)** (recomendado). Se pueden usar alternativas abiertas o gratuitas (Aider, Cline, Kilo Code…), pero hay que justificar la elección.
- Modelos **gratuitos**, por ejemplo: los modelos gratuitos de OpenCode Zen, modelos `:free` de OpenRouter, la capa gratuita de Groq o Gemini, o modelos locales con **Ollama**. Los mismos modelos se pueden usar dentro de n8n en los nodos de IA.
- **[n8n-mcp](https://github.com/czlonkowski/n8n-mcp)** (recomendado): servidor MCP que da al agente la documentación de todos los nodos de n8n y, conectado a la API de vuestra instancia, le permite crear, validar y actualizar flujos.
- Si tienen IAs de pago pueden utilizarlas, solo que tenerlo en cuenta para no pisar el trabajo del equipo, delimitar muy bien el alcance que tendrán.

**¿En qué ayuda el agente si n8n es visual?**

Un flujo de n8n es un archivo JSON y n8n tiene una API REST, así que un agente puede trabajar con ellos igual que con código:

- **Generar y modificar flujos:** a partir de una spec, el agente crea el JSON del flujo y lo sube a n8n (vía MCP o la API). El equipo lo abre en el editor, lo prueba y lo ajusta.
- **Elegir y configurar nodos:** consulta qué nodo usar y qué parámetros necesita, en lugar de buscarlo a mano en la documentación.
- **Escribir el código de los nodos Code** y las expresiones complejas (`{{ $json... }}`) de transformación de datos.
- **Depurar:** se le pasa el error de una ejecución fallida y el JSON del flujo, y propone la corrección.
- **Infraestructura y pruebas:** `docker-compose.yml`, `.env.example`, payloads de prueba para los webhooks y scripts para exportar e importar flujos.
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
2. Diseño de las hojas de Google Sheets (columnas y relaciones entre ellas)
3. Repositorio en GitHub con los flujos exportados en JSON y README con instrucciones para levantar n8n, importarlos y configurarlos
4. `docker-compose.yml` y `.env.example` para levantar n8n en local con un solo comando
5. Datos de prueba y evidencias de ejecución (capturas o vídeo de un apartado completo: alta, abonos, liquidación)
6. Tablero Kanban con historias de usuario (por ejemplo: *"Como dependienta quiero registrar un abono en menos de 30 segundos para no hacer esperar al cliente"*)
7. `AGENTS.md` y carpeta `specs/` con las especificaciones de cada automatización
8. **Bitácora de IA** (`docs/ai-log.md`): herramienta y modelos usados, prompts clave, errores o alucinaciones del agente y cómo se corrigieron
9. Historial de PRs con revisiones visibles de los flujos generados
10. Breve retrospectiva de la pareja

## 🏆 Niveles de Entrega

### 🟢 Nivel Esencial

- n8n levantado con `docker-compose` y datos persistentes en un volumen
- Google Sheets diseñado con hojas separadas para apartados, abonos y ventas
- Flujos **1 (Nuevo apartado)**, **2 (Registrar abono)** y **4 (Cierre diario)** funcionando
- Reglas validadas: abono inicial mínimo de 5 €, plazo de 3 meses y no se puede pagar más de lo que falta
- Confirmación al cliente por correo o Telegram al apartar y al abonar
- **Error Workflow** que avise a la tienda
- Credenciales gestionadas en n8n y flujos exportados en JSON en GitHub
- `AGENTS.md` funcional y bitácora de IA con al menos los prompts de cada flujo principal

### 🟡 Nivel Medio

- Flujos **3 (Venta directa)**, **5 (Recordatorios y vencimientos)** y **6 (Informe mensual)**
- Vales de compra generados al vencer un apartado y canjeables en una venta
- Sub-workflows reutilizables (**Execute Workflow**), por ejemplo "buscar apartado" o "enviar notificación"
- **Migración del Excel actual**: flujo que importe los CSV de `data/`, limpie los datos (fechas, nombres, importes) y deje en un informe los casos dudosos
- Informe mensual en PDF o con tabla en el correo
- Comparativa de al menos 2 modelos gratuitos en una misma tarea (calidad, velocidad, errores)

### 🟠 Nivel Avanzado

- **Asistente de IA por Telegram** (nodo AI Agent con un modelo gratuito y herramientas sobre las hojas):
  - el cliente pregunta *"¿cuánto me falta?"* y recibe su saldo y fecha límite
  - Marisa pregunta *"¿cuánto se recaudó esta semana?"* o *"¿qué apartados vencen este mes?"*
- Mensajes de recordatorio redactados por IA con un tono cercano, siempre con los importes calculados por el flujo (nunca por el modelo)
- Persistencia en **PostgreSQL** en lugar de Google Sheets
- Webhooks y formularios protegidos (autenticación) y validación de todos los datos de entrada
- Datos personales conforme al RGPD: solo los datos necesarios, consentimiento para recibir mensajes y no enviar teléfonos ni nombres a modelos externos
- Comandos, skills o subagentes personalizados en OpenCode para tareas repetitivas (generar specs, revisar flujos…)

### 🔴 Nivel Experto

- Panel sencillo para Marisa (Looker Studio, una web o similar) con ventas, recaudación, pendiente de cobro y apartados por vencer
- n8n con PostgreSQL en `docker-compose`, con copias de seguridad automáticas
- Despliegue en la nube (Render, Railway, un VPS, Google Cloud, etc.) con HTTPS
- Pipeline de CI con GitHub Actions que valide los JSON de los flujos en cada PR
- Exponer los flujos como servidor MCP (**MCP Server Trigger**) para que otros agentes consulten el estado de los apartados
