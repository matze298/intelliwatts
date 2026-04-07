/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/**/*.js", // In case there's JS that manipulates classes
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}