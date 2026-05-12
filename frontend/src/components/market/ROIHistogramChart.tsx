import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useRoiHistogram } from '@/hooks/useMarketStats'
import { formatInteger, formatROI } from '@/lib/utils'

export function ROIHistogramChart() {
  const histogramQuery = useRoiHistogram(10)
  const data =
    histogramQuery.data?.buckets.map((bucket) => ({
      range: `${formatROI(bucket.min_roi)}-${formatROI(bucket.max_roi)}`,
      count: bucket.count,
    })) ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle>Distribucion ROI</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-72">
          {histogramQuery.isError ? <ChartState text="No se pudo cargar el histograma." /> : null}
          {!histogramQuery.isError && histogramQuery.isLoading ? (
            <ChartState text="Cargando distribucion..." />
          ) : null}
          {!histogramQuery.isError && !histogramQuery.isLoading && data.length === 0 ? (
            <ChartState text="Sin datos de distribucion ROI." />
          ) : null}
          {data.length > 0 ? (
            <ResponsiveContainer height="100%" width="100%">
              <BarChart data={data} margin={{ bottom: 0, left: 0, right: 12, top: 8 }}>
                <CartesianGrid stroke="hsl(var(--border))" vertical={false} />
                <XAxis
                  dataKey="range"
                  fontSize={12}
                  stroke="hsl(var(--muted-foreground))"
                  tickLine={false}
                />
                <YAxis
                  fontSize={12}
                  stroke="hsl(var(--muted-foreground))"
                  tickFormatter={(value) => formatInteger(Number(value))}
                  tickLine={false}
                  width={48}
                />
                <Tooltip
                  contentStyle={{
                    background: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: 8,
                    color: 'hsl(var(--foreground))',
                  }}
                />
                <Bar dataKey="count" fill="hsl(var(--secondary))" radius={[4, 4, 0, 0]} />
              </BarChart>
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
