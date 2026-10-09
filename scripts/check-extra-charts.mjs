// Check de los 4 builders nuevos. Corre: node scripts/check-extra-charts.mjs
// El gauge es el único con aritmética no trivial (max cae a 1 para no dividir
// por cero, y el markPoint se ancla en coordenadas relativas).
import assert from 'node:assert/strict';
import { buildExtraChartOption } from '../src/features/dashboard/components/charts/extraChartConfig.ts';
import { THEME_COLORS } from '../src/features/dashboard/components/charts/theme.ts';

const rows = [
  { region: 'Norte', monto: 120 },
  { region: 'Sur', monto: 340 },
  { region: 'Este', monto: 90 },
  { region: 'Oeste', monto: 250 },
];

const base = {
  processedRows: rows,
  catCol: 'region',
  numCol: 'monto',
  currentTheme: THEME_COLORS.indigo,
  isCurrency: true,
  totalVal: rows.reduce((s, r) => s + r.monto, 0),
};

// gauge colapsa N filas a 1 cifra (el promedio), asi que se excluye del conteo.
const kinds = ['radial', 'scatter', 'treemap'];
for (const kind of kinds) {
  const opt = buildExtraChartOption({ ...base, activeChartType: kind });
  assert(opt.series[0].type.length > 0, `${kind}: sin serie`);
  assert(opt.series[0].data.length === rows.length, `${kind}: pierde filas`);
}
assert(
  buildExtraChartOption({ ...base, activeChartType: 'radial' }).angleAxis.data.length === 4,
  'radial: angleAxis sin categorias'
);
assert(
  buildExtraChartOption({ ...base, activeChartType: 'treemap' }).series[0].data[1].value === 340,
  'treemap: valor mal mapeado'
);

// Todos los valores en cero: max cae a 1 para no producir un eje degenerado.
const zero = buildExtraChartOption({
  ...base,
  processedRows: [{ region: 'A', monto: 0 }],
  totalVal: 0,
  activeChartType: 'gauge',
});
assert(zero.series[0].max === 1, 'gauge: max debe caer a 1 con datos en cero');

// El gauge muestra el promedio contra el max: average <= max siempre, asi que
// la aguja nunca satura. (Con total contra max el grafico no informaba nada.)
const g = buildExtraChartOption({ ...base, activeChartType: 'gauge' });
assert(g.series[0].max === 340, 'gauge: max incorrecto');
assert(g.series[0].data.length === 1, 'gauge: debe colapsar a una cifra');
assert(g.series[0].data[0].value === 200, 'gauge: deberia mostrar el promedio (200)');
assert(g.series[0].data[0].value <= g.series[0].max, 'gauge: la aguja saturaria');

console.log('extraChartConfig: 4 builders OK');