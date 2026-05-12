import { expect, test } from '@playwright/test'

const listings = [
  {
    id: 101,
    portal: 'milanuncios',
    ad_id: 'm-101',
    brand: 'BMW',
    model: '320d',
    year: 2019,
    mileage: 85000,
    price: 12500,
    market_price: 15200,
    roi_bruto: 21.6,
    roi_neto: 31.2,
    repair_cost: 450,
    condition_score: 72,
    images_count: 8,
    seller_type: 'particular',
    location: 'Madrid',
    price_history: [
      { price: 13000, scraped_at: '2026-05-01T10:00:00' },
      { price: 12500, scraped_at: '2026-05-08T10:00:00' },
    ],
    forensic_status: 'warning',
    forensic_summary: 'Revision pendiente de paragolpes delantero.',
    url: 'https://example.test/listing/101',
    scraped_at: '2026-05-08T10:00:00',
  },
]

test.beforeEach(async ({ page }) => {
  await page.route('**:8000/auth/login', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      json: {
        access_token: 'access-token',
        refresh_token: 'refresh-token',
        token_type: 'bearer',
        expires_in: 3600,
      },
    })
  })
  await page.route('**:8000/auth/logout', async (route) => {
    await route.fulfill({ status: 204 })
  })
  await page.route('**:8000/market/stats', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      json: {
        total_listings: 1,
        total_opportunities: 1,
        avg_roi_neto: 31.2,
        avg_price: 12500,
        avg_market_price: 15200,
        by_brand: [],
      },
    })
  })
  await page.route('**:8000/market/by-brand**', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      json: [
        {
          brand: 'BMW',
          listings_count: 1,
          avg_price: 12500,
          avg_market_price: 15200,
          avg_roi_neto: 31.2,
          opportunities_count: 1,
        },
      ],
    })
  })
  await page.route('**:8000/market/trends**', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      json: {
        brand: null,
        model: null,
        year: null,
        points: [
          { date: '2026-05-01', avg_price: 13000, listings_count: 1 },
          { date: '2026-05-08', avg_price: 12500, listings_count: 1 },
        ],
      },
    })
  })
  await page.route('**:8000/market/roi-histogram**', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      json: {
        buckets: [{ min_roi: 30, max_roi: 40, count: 1 }],
        total_count: 1,
      },
    })
  })
  await page.route('**:8000/listings/101', async (route) => {
    await route.fulfill({ contentType: 'application/json', json: listings[0] })
  })
  await page.route('**:8000/listings**', async (route) => {
    if (new URL(route.request().url()).pathname === '/listings/101') {
      await route.fulfill({ contentType: 'application/json', json: listings[0] })
      return
    }
    await route.fulfill({
      contentType: 'application/json',
      json: { items: listings, total: 1, page: 1, size: 25 },
    })
  })
})

test('dealer can log in, inspect listings, and save a search', async ({ page }) => {
  await page.addInitScript(() => localStorage.clear())
  await page.goto('/login')
  await expect(page.getByText('Acceso dealer')).toBeVisible()

  await page.getByLabel('Email').fill('dealer@agartha.local')
  await page.getByLabel('Password').fill('supersecret')
  await page.getByRole('button', { name: 'Entrar' }).click()

  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await expect(page.getByText('BMW 320d')).toBeVisible()

  await page.getByRole('button', { name: /BMW 320d/ }).click()
  await expect(page.getByRole('dialog')).toContainText('Revision pendiente')
  await page.getByRole('button', { name: 'Cerrar detalle' }).click()

  await page.getByRole('link', { name: 'Busquedas' }).click()
  await page.getByPlaceholder('Nombre de la busqueda actual').fill('BMW ROI alto')
  await page.getByRole('button', { name: 'Guardar actual' }).click()
  await expect(page.getByText('BMW ROI alto')).toBeVisible()

  await page.getByRole('button', { name: 'Cerrar sesion' }).click()
  await expect(page).toHaveURL(/\/login$/)
})
