/**
 * Lista canônica de cores de veículo para os dropdowns de cadastro e consulta.
 *
 * Fonte única consumida pelas páginas de nova abordagem (cadastro de veículo)
 * e de consulta (filtro por cor). Mantida no frontend por ser puramente
 * apresentacional e para funcionar offline (PWA). A busca por cor no backend
 * trata flexão de gênero (branco/branca) de forma independente, cobrindo dados
 * antigos com grafia mista.
 */
window.CORES_VEICULO = [
  "Branco",
  "Preto",
  "Prata",
  "Cinza",
  "Vermelho",
  "Azul",
  "Verde",
  "Amarelo",
  "Marrom",
  "Bege",
  "Dourado",
  "Laranja",
  "Vinho",
  "Rosa",
  "Roxo",
  "Grafite",
  "Fantasia",
];
