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
import { useBrandMetrics } from '@/hooks/useMarketStats'
import { formatROI } from '@/lib/utils'

export function ROIBarChart() {
  const brandMetricsQuery = useBrandMetrics(10)
  const data =
    brandMetricsQuery.data
      ?.filter((item) => item.avg_roi_neto != null)
      .map((item) => ({
        brand: item.brand,
        roi: Number(item.avg_roi_neto),
        opportunities: item.opportunities_count,
      })) ?? []

  return (
    <Card>
      <CardHeader>
        <CardTitle>ROI medio por marca</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-72">
          {brandMetricsQuery.isError ? (
            <ChartState text="No se pudo cargar `/market/by-brand`." />
          ) : null}
          {!brandMetricsQuery.isError && brandMetricsQuery.isLoading ? (
            <ChartState text="Cargando ROI por marca..." />
          ) : null}
          {!brandMetricsQuery.isError &&
          !brandMetricsQuery.isLoading &&
          data.length === 0 ? (
            <ChartState text="Sin datos de ROI por marca." />
          ) : null}
          {data.length > 0 ? (
            <ResponsiveContainer height="100%" width="100%">
              <BarChart data={data} margin={{ bottom: 0, left: 0, right: 12, top: 8 }}>
                <CartesianGrid stroke="hsl(var(--border))" vertical={false} />
                <XAxis
                  dataKey="brand"
                  fontSize={12}
                  stroke="hsl(var(--muted-foreground))"
                  tickLine={false}
                />
                <YAxis
                  fontSize={12}
                  stroke="hsl(var(--muted-foreground))"
                  tickFormatter={(value) => formatROI(Number(value))}
                  tickLine={false}
                  width={52}
                />
                <Tooltip
                  contentStyle={{
                    background: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: 8,
                    color: 'hsl(var(--foreground))',
                  }}
                  formatter={(value, name) => [
                    name === 'roi' ? formatROI(Number(value)) : value,
                    name === 'roi' ? 'ROI medio' : 'Oportunidades',
                  ]}
                />
                <Bar dataKey="roi" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
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
