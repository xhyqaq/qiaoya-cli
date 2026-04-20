#!/usr/bin/env node

const { main } = require('../src/bootstrap');

main(process.argv.slice(2)).catch((error) => {
  console.error(error.message || String(error));
  process.exit(1);
});
