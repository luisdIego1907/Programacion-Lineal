# Programación lineal: simplex y método gráfico

Aplicación educativa en **Python y Streamlit**, en español, para modelos con **dos variables de decisión, tres restricciones y no negatividad**. El simplex está implementado explícitamente; ningún optimizador resuelve los modelos de la aplicación.

## Inicio rápido en Windows

Con Python 3.11 o posterior instalado, abra **`iniciar.bat`**. El iniciador prepara un entorno virtual, instala las dependencias que falten y abre la herramienta en el navegador.

También puede ejecutar estos comandos desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Dirección local habitual: [http://localhost:8501](http://localhost:8501). Para detener la aplicación, presione `Ctrl+C` en la terminal.

En macOS o Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Uso

1. Seleccione **Maximizar** o **Minimizar**.
2. Escriba los dos coeficientes del objetivo y las tres restricciones. Se aceptan `≤`, `≥`, `=`, coeficientes negativos, lados derechos negativos, decimales con coma o punto y fracciones como `1/3`. Si una variable no aparece, use coeficiente `0`.
3. Presione **Resolver modelo**. El panel derecho muestra el modelo que se está resolviendo.
4. Revise las cuatro pestañas: resultado e interpretación, simplex paso a paso, método gráfico y verificación con descarga.
5. Edite los datos y vuelva a resolver, o cargue otro ejemplo desde la barra lateral.

Las tablas muestran fracciones exactas. Solo se convierten a punto flotante las coordenadas usadas para dibujar. Los límites de la gráfica se pueden cambiar sin modificar el problema. Pase el cursor por los puntos para consultar coordenadas y valores; use la cámara de Plotly para guardar un SVG.

## Contenido de la solución

| Requisito | Implementación |
| --- | --- |
| Formulación | Objetivo max/min, dos variables, tres restricciones con signos combinados y no negatividad explícita. |
| Transformación | Normalización de lados derechos, variables de holgura, superávit y artificiales. |
| Simplex | Tabla inicial, costos Cj y Cb, Zj, costos reducidos, entrada, salida, razones, pivote, operaciones de Gauss–Jordan y tabla de cada iteración. |
| Método de la M | Penalización **simbólica**, sin elegir un valor numérico de M. |
| Gráfico | Rectas, región factible, vértices exactos, evaluación de Z, óptimos y direcciones no acotadas. También admite regiones que sean segmentos o puntos. |
| Resultados | x1, x2, Z, holguras/superávits, restricciones activas y explicación matemática. |
| Casos especiales | Infactibilidad, objetivo no acotado, degeneración, redundancia y múltiples óptimos. |
| Comparación | La geometría calcula su propio resultado y lo contrasta con simplex. |
| Evidencia | Seis ejemplos conocidos y pruebas automáticas del algoritmo y de la interfaz. |
| Exportación | Procedimiento completo en Markdown y datos exactos del modelo en JSON. |

## Organización del código

```text
app.py                   Interfaz y validación de entradas
lp/model.py              Modelo, restricciones y números racionales
lp/simplex.py            Forma estándar, M simbólica, pivotes y traza
lp/geometry.py           Intersecciones, vértices y cono de recesión
lp/plotting.py           Gráfica interactiva con Plotly
lp/presentation.py       Fórmulas, tablas y reporte descargable
lp/examples.py           Seis modelos con resultados conocidos
tests/test_solver.py     Casos matemáticos y propiedades de las tablas
tests/test_oracle.py     500 modelos frente a SciPy/HiGHS, solo como prueba
tests/test_ui.py         Interacción simulada con Streamlit AppTest
generar_reportes.py      Regenera los ejemplos resueltos y su verificación
ejemplos_resueltos/      Procedimientos completos de los seis ejemplos
METODOLOGIA.md           Explicación del algoritmo y sus criterios
VERIFICACION.md          Resultados de la ejecución de las pruebas
requirements.txt         Dependencias de la aplicación
requirements-dev.txt     Añade SciPy para la comparación de pruebas
```

## Ejemplos de verificación

Todos suponen x1, x2 ≥ 0.

| Ejemplo | Objetivo | Tres restricciones | Resultado esperado |
| --- | --- | --- | --- |
| 1. Maximización | Max 3x1 + 2x2 | x1+x2 ≤ 4; x1 ≤ 2; x2 ≤ 3 | (2, 2), Z = 10 |
| 2. Minimización | Min 2x1 + 3x2 | x1+x2 ≥ 4; x1+3x2 ≥ 6; x1 ≤ 5 | (3, 1), Z = 9; requiere artificiales |
| 3. Signos mixtos | Max 2x1 + 3x2 | x1+x2 = 5; x1 ≥ 1; x2 ≤ 3 | (2, 3), Z = 13; requiere artificiales |
| 4. Infactible | Max x1 + x2 | x1+x2 ≤ 1; x1+x2 ≥ 3; x1 ≤ 4 | No existe punto factible |
| 5. No acotado | Max x1 + x2 | x1−x2 ≥ 0; −x1+2x2 ≥ 0; x2 ≥ 1 | Z puede crecer sin límite |
| 6. Óptimos múltiples | Max x1 + x2 | x1+x2 ≤ 4; x1 ≤ 3; x2 ≤ 3 | Segmento de (1, 3) a (3, 1), Z = 4 |

Para ejecutar las pruebas básicas, con las dependencias de la aplicación instaladas:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para incluir la comparación con HiGHS:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

SciPy es opcional y se utiliza exclusivamente dentro de las pruebas. El programa no lo importa para resolver modelos. La prueba de referencia se omite con un mensaje si no está instalado.

Puede regenerar los procedimientos entregados con:

```powershell
.\.venv\Scripts\python.exe generar_reportes.py
```

## Reto opcional: publicar en Streamlit Community Cloud

La aplicación está preparada para desplegarse, pero esta entrega no crea una cuenta, un repositorio remoto ni una publicación. Para completar el reto se necesita una cuenta de GitHub y una de Streamlit Community Cloud.

1. Suba el **contenido de esta carpeta** a la raíz de un repositorio de GitHub. Incluya `app.py`, `lp/`, `requirements.txt` y `.streamlit/config.toml`. No suba `.venv`, archivos temporales ni secretos.
2. Entre en [Streamlit Community Cloud](https://share.streamlit.io/), cree una aplicación y seleccione ese repositorio y su rama.
3. Seleccione **`app.py`** como archivo de entrada. En las opciones avanzadas seleccione **Python 3.13**, versión con la que se verificó esta entrega.
4. Despliegue y compruebe los seis ejemplos desde la dirección pública que genere la plataforma. Esa URL es la que debe adjuntar como evidencia del reto opcional.

Consulte la [guía oficial de publicación](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) para los pasos actuales del servicio. Si mantiene el proyecto dentro de una subcarpeta del repositorio, seleccione la ruta completa a `app.py` como entrada.

## Referencias técnicas

- [Documentación de Streamlit](https://docs.streamlit.io/).
- [Pruebas de interfaz con AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
- [Gráficas Plotly en Streamlit](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart).
- [Aritmética racional con fractions.Fraction](https://docs.python.org/3/library/fractions.html).

Antes de presentar el ejercicio, revise `METODOLOGIA.md` y los ejemplos resueltos para poder explicar los criterios de entrada, salida y terminación.
