/* Entradas iniciales del blog. Las que crea el usuario se añaden a estas desde localStorage. */
// biome-ignore lint/correctness/noUnusedVariables: se usa desde app.js (scripts clásicos con ámbito global compartido)
const CATEGORIES = ["Desarrollo web", "Seguridad", "Derecho digital", "Vida universitaria"];

// biome-ignore lint/correctness/noUnusedVariables: se usa desde app.js (scripts clásicos con ámbito global compartido)
const SEED_POSTS = [
  {
    id: "seed-html5-semantica",
    title: "Por qué importa el HTML semántico",
    category: "Desarrollo web",
    tags: ["html", "accesibilidad", "seo"],
    date: "2026-09-18",
    content: [
      "Durante mis primeras páginas lo hacía todo con <div>. Funcionaba, pero el documento no decía nada de sí mismo. HTML5 trae etiquetas como <header>, <nav>, <main>, <article> y <footer> que describen el papel de cada bloque.",
      "Esa estructura no es solo estética para el código. Los lectores de pantalla la usan para saltar entre regiones, y los buscadores la aprovechan para entender qué es el contenido principal y qué es navegación.",
      "Mi regla actual: si existe una etiqueta con el significado que necesito, la uso; y solo recurro a <div> o <span> cuando lo único que quiero es agrupar para dar estilo.",
    ],
  },
  {
    id: "seed-css-flex-grid",
    title: "Flexbox y Grid: cuándo uso cada uno",
    category: "Desarrollo web",
    tags: ["css", "layout", "responsive"],
    date: "2026-09-15",
    content: [
      "Flexbox está pensado para distribuir elementos en una sola dimensión: una fila de botones, una barra de navegación, el contenido centrado dentro de una tarjeta.",
      "Grid es mi elección cuando necesito controlar filas y columnas a la vez, como el listado de entradas de este blog. Con grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)) obtengo un diseño adaptable sin escribir ni una media query.",
      "Y no son excluyentes: una tarjeta dentro de una rejilla Grid puede usar Flexbox por dentro para alinear su pie.",
    ],
  },
  {
    id: "seed-js-dom",
    title: "Manipular el DOM sin librerías",
    category: "Desarrollo web",
    tags: ["javascript", "dom", "seguridad"],
    date: "2026-09-12",
    content: [
      "Se puede construir toda una interfaz con document.createElement, textContent y addEventListener. Es más verboso que usar un framework, pero se entiende perfectamente qué ocurre en cada paso.",
      "Un detalle importante: cuando el texto lo escribe un usuario, nunca lo inserto con innerHTML. Con textContent el navegador lo trata como texto y no como código, lo que evita inyecciones de HTML o scripts.",
      "Para guardar datos entre visitas uso localStorage, siempre dentro de un try/catch porque puede estar bloqueado o lleno.",
    ],
  },
  {
    id: "seed-contrasenas",
    title: "Contraseñas: longitud antes que rareza",
    category: "Seguridad",
    tags: ["autenticacion", "buenas-practicas"],
    date: "2026-09-09",
    content: [
      "Durante años nos dijeron que una buena contraseña mezcla mayúsculas, símbolos y números. Las recomendaciones actuales, como las del NIST, priorizan la longitud y desaconsejan forzar cambios periódicos sin motivo.",
      "Una frase larga y fácil de recordar resiste mejor un ataque de fuerza bruta que una palabra corta con sustituciones previsibles como «P@ssw0rd».",
      "Lo esencial sigue siendo no reutilizarlas entre servicios, usar un gestor de contraseñas y activar la verificación en dos pasos siempre que se pueda.",
    ],
  },
  {
    id: "seed-https",
    title: "Qué hace realmente el candado de HTTPS",
    category: "Seguridad",
    tags: ["https", "tls", "redes"],
    date: "2026-09-05",
    content: [
      "HTTPS es HTTP sobre TLS. El candado indica que la conexión entre tu navegador y el servidor está cifrada y que el certificado del servidor es válido para ese dominio.",
      "Lo que no garantiza es que la web sea de fiar: una página de phishing también puede tener un certificado válido. El candado protege el canal, no las intenciones de quien está al otro lado.",
    ],
  },
  {
    id: "seed-cookies",
    title: "Cookies y consentimiento: lo que exige la ley",
    category: "Derecho digital",
    tags: ["cookies", "rgpd", "lssi"],
    date: "2026-09-02",
    content: [
      "En España, el artículo 22.2 de la LSSI exige consentimiento informado para instalar cookies que no sean estrictamente necesarias, y el RGPD define cómo debe ser ese consentimiento: libre, específico, informado e inequívoco.",
      "En la práctica, eso significa que seguir navegando no vale como aceptación, que rechazar debe ser tan fácil como aceptar y que el usuario debe poder retirar su consentimiento cuando quiera.",
      "Al diseñar un blog con analítica esto me condiciona: si no necesito medir visitas, lo más sencillo y respetuoso es no instalar cookies.",
    ],
  },
  {
    id: "seed-organizacion",
    title: "Cómo organizo el estudio con trabajo y varias asignaturas",
    category: "Vida universitaria",
    tags: ["organizacion", "productividad"],
    date: "2026-08-29",
    content: [
      "Compagino los estudios con el trabajo, así que el tiempo es el recurso escaso. Cada domingo reparto las entregas de la semana en bloques de dos horas y los pongo en el calendario como si fueran reuniones.",
      "Empiezo siempre por la actividad con fecha más cercana y dejo lo más creativo para cuando tengo más energía. Revisar al final del día qué he avanzado me ayuda a no acumular tareas.",
    ],
  },
  {
    id: "seed-git",
    title: "Commits pequeños: por qué integrar cada día",
    category: "Vida universitaria",
    tags: ["git", "trabajo-en-equipo"],
    date: "2026-08-25",
    content: [
      "Trabajar con ramas que viven muchos días acumula el riesgo en lugar de eliminarlo: cuanto más tarde integras, más conflictos y más sorpresas.",
      "Prefiero commits pequeños con un mensaje claro y volver a la rama principal a diario. Así el historial cuenta lo que pasó y cualquier cambio es fácil de revertir.",
    ],
  },
];
