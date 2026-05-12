import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { usePriceTrend } from '@/hooks/useMarketStats'
import { formatCurrency } from '@/lib/utils'

export function PriceTrendChart({
  brand,
  model,
  year,
}: {
  brand?: string
  model?: string
  year?: number
}) {
  const trendQuery = usePriceTrend({ brand, model, year })
  const data =
    trendQuery.data?.points.map((point) => ({
      date: String(point.date).slice(0, 10),
      avg_price: point.avg_price,
      listings_count: point.listings_count,
    })) ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tendencia de precio</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-72">
          {trendQuery.isError ? <ChartState text="No se pudo cargar `/market/trends`." /> : null}
          {!trendQuery.isError && trendQuery.isLoading ? (
            <ChartState text="Cargando tendencia..." />
          ) : null}
          {!trendQuery.isError && !trendQuery.isLoading && data.length === 0 ? (
            <ChartState text="Sin historial de precios todavia." />
          ) : null}
          {data.length > 0 ? (
            <ResponsiveContainer height="100%" width="100%">
              <LineChart data={data} margin={{ bottom: 0, left: 0, right: 12, top: 8 }}>
                <CartesianGrid stroke="hsl(var(--border))" vertical={false} />
                <XAxis
                  dataKey="date"
                  fontSize={12}
                  stroke="hsl(var(--muted-foreground))"
                  tickLine={false}
                />
                <YAxis
                  fontSize={12}
                  stroke="hsl(var(--muted-foreground))"
                  tickFormatter={(value) => formatCurrency(Number(value))}
                  tickLine={false}
                  width={72}
                />
                <Tooltip
                  contentStyle={{
                    background: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: 8,
                    color: 'hsl(var(--foreground))',
                  }}
                  formatter={(value, name) => [
                    name === 'avg_price' ? formatCurrency(Number(value)) : value,
                    name === 'avg_price' ? 'Precio medio' : 'Listings',
                  ]}
                />
                <Line
                  dataKey="avg_price"
                  dot={{ r: 3 }}
                  stroke="hsl(var(--accent))"
                  strokeWidth={2}
                  type="monotone"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}

function ChartState({ text }: { text: string }) {
  return (
    <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
      {text}
    </div>
  )
}
